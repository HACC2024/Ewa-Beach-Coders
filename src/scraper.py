# src/scraper.py

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PyPDF2 import PdfReader
import csv
import glob
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from utils import log_info, log_error

def download_pdf(url, output_dir):
    """
    Downloads a PDF file from the given URL and saves it to the output directory.
    """
    try:
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        filename = os.path.basename(urlparse(url).path)
        if not filename.lower().endswith('.pdf'):  # Ensure proper extension
            filename = "downloaded_file.pdf"
        
        # To avoid filename conflicts, append a number if the file already exists
        base_filename = filename[:-4] if filename.lower().endswith('.pdf') else filename
        counter = 1
        while os.path.exists(os.path.join(output_dir, filename)):
            filename = f"{base_filename}_{counter}.pdf"
            counter += 1
        file_path = os.path.join(output_dir, filename)

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        log_info(f"Downloaded PDF: {url} -> {file_path}")
        return file_path
    except requests.exceptions.RequestException as e:
        log_error(f"Failed to download PDF {url}: {e}")
        return None

def extract_text_from_pdf(file_path):
    """
    Extracts text content from a PDF file.
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text += page_text
            else:
                log_info(f"No text found on page {page_num} of {file_path}")
        return text.strip()
    except Exception as e:
        log_error(f"Failed to extract text from PDF {file_path}: {e}")
        return None

def scrape_webpage(url, pdf_output_dir, text_output_file):
    """
    Scrapes a webpage for text and PDFs, and saves all content into a single text file.
    The first line of the text file is the source URL for citation purposes.
    """
    try:
        # Send a GET request to the webpage
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Open the text file for writing
        with open(text_output_file, 'w', encoding='utf-8') as text_file:
            # Write the source URL as the first line
            text_file.write(f"Source URL: {url}\n\n")

            # Write the text content of the page
            text_content = soup.get_text(separator=' ', strip=True)
            cleaned_text = ' '.join(text_content.split())
            text_file.write(f"TEXT CONTENT:\n{cleaned_text}\n\n")
            log_info(f"Webpage text content saved to {text_output_file}")

            # Write a header for PDF content
            text_file.write("EXTRACTED CONTENT FROM PDFs:\n")
            # Iterate over all <a> tags with href attributes
            for tag in soup.find_all('a', href=True):
                file_url = urljoin(url, tag['href'])
                if file_url.lower().endswith('.pdf'):
                    pdf_path = download_pdf(file_url, pdf_output_dir)
                    if pdf_path:
                        pdf_text = extract_text_from_pdf(pdf_path)
                        if pdf_text:
                            text_file.write(f"\n--- Text from PDF ({file_url}) ---\n")
                            text_file.write(f"{pdf_text}\n")
                            log_info(f"Extracted text from PDF: {file_url}")
    except requests.exceptions.RequestException as e:
        log_error(f"An error occurred while fetching the webpage {url}: {e}")
    except IOError as e:
        log_error(f"An error occurred while writing to the file {text_output_file}: {e}")

def delete_pdfs(output_dir):
    """
    Deletes the specified PDF directory and all its contents.
    """
    try:
        shutil.rmtree(output_dir)
        log_info(f"Deleted PDF directory: {output_dir}")
    except Exception as e:
        log_error(f"An error occurred while deleting PDF directory {output_dir}: {e}")

def process_domain(subdomain, scraped_data_folder, base_pdf_output_dir):
    """
    Processes a single domain: scrapes the webpage, extracts PDF content, and deletes PDFs.
    """
    url = f"https://{subdomain}"
    log_info(f"\nScraping URL: {url}")

    # Define the output text file path
    # Replace any invalid filename characters if necessary
    safe_subdomain = subdomain.replace('/', '_').replace('\\', '_').replace(':', '_')
    output_file = os.path.join(scraped_data_folder, f"{safe_subdomain}.txt")

    # Define a unique temporary PDF directory for this domain
    pdf_output_dir = os.path.join(base_pdf_output_dir, safe_subdomain)
    os.makedirs(pdf_output_dir, exist_ok=True)

    # Scrape the webpage and write content to the text file
    scrape_webpage(url, pdf_output_dir, output_file)

    # Delete all PDFs after processing the current domain
    delete_pdfs(pdf_output_dir)

def process_csv_files(domains_folder, scraped_data_folder, pdf_output_dir, max_workers=10):
    """
    Processes all CSV files in the domains folder and scrapes each domain using threading.
    """
    # Ensure the output directories exist
    os.makedirs(scraped_data_folder, exist_ok=True)
    os.makedirs(pdf_output_dir, exist_ok=True)

    # Get all CSV files in the domains folder
    csv_files = glob.glob(os.path.join(domains_folder, "*.csv"))

    if not csv_files:
        log_info(f"No CSV files found in the folder: {domains_folder}")
        return

    # Collect all subdomains from all CSV files
    subdomains = []
    for csv_file in csv_files:
        log_info(f"\nProcessing CSV file: {csv_file}")
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row_num, row in enumerate(reader, start=2):  # Start at 2 considering header
                    subdomain = row.get('Subdomain', '').strip()
                    if not subdomain:
                        log_info(f"Empty subdomain found at row {row_num} in {csv_file}, skipping.")
                        continue
                    subdomains.append(subdomain)
        except Exception as e:
            log_error(f"An error occurred while processing the CSV file {csv_file}: {e}")

    # Use ThreadPoolExecutor to process domains concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Initialize tqdm progress bar
        with tqdm(total=len(subdomains), desc="Scraping Domains", unit="domain") as pbar:
            # Submit all tasks
            future_to_subdomain = {
                executor.submit(process_domain, subdomain, scraped_data_folder, pdf_output_dir): subdomain
                for subdomain in subdomains
            }

            # Iterate over completed futures
            for future in as_completed(future_to_subdomain):
                subdomain = future_to_subdomain[future]
                try:
                    future.result()
                except Exception as e:
                    log_error(f"An error occurred while processing {subdomain}: {e}")
                finally:
                    pbar.update(1)

def main():
    # Define directories
    project_dir = os.path.dirname(os.path.abspath(__file__))
    domains_folder = os.path.join(project_dir, "..", "domains")
    scraped_data_folder = os.path.join(project_dir, "..", "Scraped Data")
    base_pdf_output_dir = os.path.join(project_dir, "..", "downloaded_pdfs")  # Temporarily stored PDFs

    # Define the number of worker threads
    max_workers = 10  # Adjust based on your system's capabilities

    # Process all CSV files and scrape domains
    process_csv_files(domains_folder, scraped_data_folder, base_pdf_output_dir, max_workers=max_workers)

    log_info("\nScraping completed.")

if __name__ == "__main__":
    main()
