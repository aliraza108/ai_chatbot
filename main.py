# main.py
import os
import re
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import warnings

# Import necessary components from LlamaIndex
from llama_index import GPTVectorStoreIndex, Document, ServiceContext
from llama_index.llms import OpenAI

warnings.filterwarnings("ignore")

# Load environment variables (if any)
load_dotenv()

# Use the provided API key
OPENAI_API_KEY = (
    "sk-proj-"
    + "p2dN0_oztdhFKtMjji9f5DGI7XQPFEORui43AF1arpd57VAdcEc2sHI77mSk5YX74uqgYIQYAwT3BlbkFJ_Bokz-n5mwr6coif3oieLYHu-6Xz5hxawV2mlKXtpTAOiyXiKWm6jtv5e7FOLlew8fSYFiU68A"
)

def build_index(products_df):
    """
    Build a LlamaIndex vector store index from your product CSV.
    Each product becomes a document with its details.
    """
    documents = []
    for _, row in products_df.iterrows():
        doc_text = (
            f"Product Title: {row['title']}\n"
            f"Price: ${row['price']}\n"
            f"Product URL: {row['product_url']}\n"
            f"Image URL: {row['image_url']}"
        )
        documents.append(Document(text=doc_text))
    
    # Create a service context using the provided OpenAI API key and model.
    service_context = ServiceContext.from_defaults(
        llm=OpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)
    )
    index = GPTVectorStoreIndex.from_documents(documents, service_context=service_context)
    return index

def enhance_product_display(response_text, products_df):
    """
    Replace product title markers (wrapped in <h3> tags) with styled product cards.
    Each card includes the product image, price, and a "View Product" button.
    """
    pattern = r'<h3>(.*?)<\/h3>'
    matches = list(re.finditer(pattern, response_text))
    for match in reversed(matches):
        title = match.group(1).strip()
        product_match = products_df[products_df['title'] == title]
        if not product_match.empty:
            product = product_match.iloc[0]
            card_html = f"""
            <div class="product-card">
                <h3>{product['title']}</h3>
                <img src="{product['image_url']}" width="100" style="max-width:100%; height:auto;" alt="{product['title']}">
                <p>Price: ${product['price']}</p>
                <a href="{product['product_url']}" target="_blank">
                    <button>View Product</button>
                </a>
            </div>
            """
            # Replace the matched title with the full product card.
            response_text = response_text[:match.start()] + card_html + response_text[match.end():]
    return response_text

def apply_styles():
    """Apply CSS styling for product cards and buttons."""
    st.markdown("""
    <style>
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        background: white;
    }
    button {
        background: #4CAF50;
        color: white;
        padding: 8px 16px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    button:hover {
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True)

def init_session():
    """
    Initialize Streamlit session state for:
      - Chat history
      - Loading the product CSV
      - Building the LlamaIndex vector store
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "products_df" not in st.session_state:
        csv_path = os.path.join("data", "pro.csv")
        st.session_state.products_df = pd.read_csv(csv_path)
    if "index" not in st.session_state:
        st.session_state.index = build_index(st.session_state.products_df)

def main():
    st.title("🛍️✨ Product Chatbot")
    apply_styles()
    init_session()

    # Display chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").markdown(msg["content"])
        else:
            st.chat_message("assistant").markdown(msg["content"], unsafe_allow_html=True)

    # Chat input box
    if prompt := st.chat_input("Ask about products..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        # Query the index with the user prompt (returning top 3 matches)
        response = st.session_state.index.query(prompt, similarity_top_k=3)
        matched_docs = response.source_nodes
        
        # Create a new response by wrapping product titles in <h3> tags.
        if matched_docs:
            new_response = ""
            for doc in matched_docs:
                m = re.search(r'Product Title:\s*(.*)', doc.node.text)
                if m:
                    product_title = m.group(1).strip()
                    new_response += f"<h3>{product_title}</h3>\n"
            processed = enhance_product_display(new_response, st.session_state.products_df)
        else:
            processed = response.response

        st.chat_message("assistant").markdown(processed, unsafe_allow_html=True)
        st.session_state.messages.append({"role": "assistant", "content": processed})

if __name__ == "__main__":
    main()
