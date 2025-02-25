import re
import streamlit as st
import pandas as pd
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool  # ← Critical import
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Configuration
OPENAI_API_KEY = "sk-proj-..."  # Your full key
Settings.llm = OpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")
Settings.embed_model = OpenAIEmbedding(api_key=OPENAI_API_KEY)

def enhance_product_display(response_text: str) -> str:
    pattern = r'\[PRODUCT\](.*?)\[\/PRODUCT\]'
    products = re.findall(pattern, response_text, re.IGNORECASE)
    
    for product_title in products:
        product = st.session_state.products_df[
            st.session_state.products_df['Title'].str.contains(product_title, case=False)
        ].iloc[0] if not st.session_state.products_df.empty else None
        
        if product is not None:
            card_html = f"""
            <div class="product-card" style="border:1px solid #ddd; padding:10px; margin:10px; border-radius:5px;">
                <h4>{product['Title']}</h4>
                <img src="{product['Image Src']}" width="100" style="max-width:100%; height:auto;">
                <p>Price: ${product['Variant Price']:,.2f}</p>
                <a href="https://yourstore.com/products/{product['Handle']}" target="_blank">
                    <button style="background:#4CAF50; color:white; border:none; padding:8px; border-radius:4px;">
                        View Product
                    </button>
                </a>
            </div>
            """
            response_text = response_text.replace(f"[PRODUCT]{product_title}[/PRODUCT]", card_html)
    return response_text

def get_all_products(query: str) -> str:
    products = st.session_state.products_df[
        st.session_state.products_df['Title'].str.contains(query, case=False)
    ].head(10)
    return "\n".join([f"[PRODUCT]{row['Title']}[/PRODUCT]" for _, row in products.iterrows()])

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []  # ← Initialize messages
        
    if "products_df" not in st.session_state:
        st.session_state.products_df = pd.read_csv("product.csv")
    
    if "agent" not in st.session_state:
        tools = [FunctionTool.from_defaults(fn=get_all_products, name="product_search")]
        st.session_state.agent = ReActAgent.from_tools(
            tools=tools,
            system_prompt="Always use [PRODUCT][/PRODUCT] tags and show images+buttons"
        )

def main():
    st.title("🛍️ Product Assistant")
    init_session()
    
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"], unsafe_allow_html=True)
    
    if prompt := st.chat_input("Ask about products..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        try:
            response = st.session_state.agent.chat(prompt)
            processed = enhance_product_display(response.response)
            st.session_state.messages.append({"role": "assistant", "content": processed})
            st.chat_message("assistant").markdown(processed, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
