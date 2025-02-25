import re
import streamlit as st
import pandas as pd
from llama_index.core import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Configuration
OPENAI_API_KEY = "sk-proj-..."  # Your full API key
Settings.llm = OpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)
Settings.embed_model = OpenAIEmbedding(api_key=OPENAI_API_KEY)

def create_product_card(row):
    """Generate HTML card for a product"""
    return f"""
    <div class="product-card" style="border:1px solid #ddd; padding:15px; margin:15px; border-radius:8px;">
        <h3>{row['Title']}</h3>
        <img src="{row['Image Src']}" width="150" style="max-width:100%; height:auto;">
        <p>Price: ${row['Variant Price']:,.2f}</p>
        <a href="https://yourstore.com/products/{row['Handle']}" target="_blank">
            <button style="background:#4CAF50; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">
                View Product
            </button>
        </a>
    </div>
    """

def product_search_tool(query: str) -> str:
    """Search products and return formatted results"""
    try:
        results = st.session_state.products_df[
            st.session_state.products_df['Title'].str.contains(query, case=False, na=False)
        ].head(3)
        
        if results.empty:
            return "No products found"
            
        return "\n".join([f"[PRODUCT]{row['Title']}[/PRODUCT]" for _, row in results.iterrows()])
    
    except Exception as e:
        return f"Error searching products: {str(e)}"

def get_lowest_price_tool(query: str) -> str:
    """Find lowest priced products"""
    try:
        results = st.session_state.products_df.nsmallest(3, 'Variant Price')
        return "\n".join([f"[PRODUCT]{row['Title']}[/PRODUCT]" for _, row in results.iterrows()])
    except Exception as e:
        return f"Error finding prices: {str(e)}"

def enhance_response(response_text: str) -> str:
    """Convert [PRODUCT] tags to cards"""
    try:
        products = re.findall(r'\[PRODUCT\](.*?)\[\/PRODUCT\]', response_text, re.IGNORECASE)
        
        for product_title in products:
            product = st.session_state.products_df[
                st.session_state.products_df['Title'].str.contains(product_title, case=False, na=False)
            ].iloc[0] if not st.session_state.products_df.empty else None
            
            if product is not None:
                response_text = response_text.replace(
                    f"[PRODUCT]{product_title}[/PRODUCT]", 
                    create_product_card(product)
                )
        
        return response_text
    except Exception as e:
        return response_text

def init_session():
    """Initialize session state"""
    try:
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        if "products_df" not in st.session_state:
            st.session_state.products_df = pd.read_csv("product.csv")
            st.session_state.products_df['Variant Price'] = pd.to_numeric(
                st.session_state.products_df['Variant Price'], errors='coerce'
            )
            
        if "agent" not in st.session_state:
            tools = [
                FunctionTool.from_defaults(
                    fn=product_search_tool,
                    name="product_search",
                    description="Search for products by name or description"
                ),
                FunctionTool.from_defaults(
                    fn=get_lowest_price_tool,
                    name="lowest_price",
                    description="Find lowest priced products"
                )
            ]
            
            st.session_state.agent = ReActAgent.from_tools(
                tools=tools,
                system_prompt="""
                You are an e-commerce assistant. Follow STRICTLY:
                1. For product-related queries, ALWAYS use tools
                2. Wrap product names in [PRODUCT][/PRODUCT] tags
                3. Show max 3 products with image, price, and button
                4. For non-product queries, answer normally
                5. Never mention tools or technical details
                """
            )
            
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")
        st.stop()

def main():
    st.title("🛍️ Smart Shopping Assistant")
    init_session()
    
    # Display chat history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"], unsafe_allow_html=True)
    
    # Handle input
    if prompt := st.chat_input("Ask about products or anything..."):
        try:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").markdown(prompt)
            
            # Get response
            response = st.session_state.agent.chat(prompt)
            processed_response = enhance_response(response.response)
            
            # Add and display assistant response
            st.session_state.messages.append({"role": "assistant", "content": processed_response})
            st.chat_message("assistant").markdown(processed_response, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error processing request: {str(e)}")

if __name__ == "__main__":
    main()
