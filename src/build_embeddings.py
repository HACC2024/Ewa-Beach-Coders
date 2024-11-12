from embedding import EmbeddingStore, build_embedding_store

scraped_data_folder = "Scraped Data"
embedding_store = EmbeddingStore()
build_embedding_store(scraped_data_folder, embedding_store)
