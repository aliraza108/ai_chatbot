import os
import re
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.schema import TextNode

# Load environment variables
load_dotenv()

# Initialize OpenAI API key (use environment variables in production!)
OPENAI_API_KEY = (
    "sk-proj-" + 
    "p2dN0_oztdhFKtMjji9f5DGI7XQPFEORui43AF1arpd57VAdcEc2sHI77mSk5YX74uqgYIQYAwT3BlbkFJ_Bokz-n5mwr6coif3oieLYHu-6Xz5hxawV2mlKXtpTAOiyXiKWm6jtv5e7FOLlew8fSYFiU68A"
)

# Configure global settings
try:
    Settings.llm = OpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0.1)
    Settings.embed_model = OpenAIEmbedding(api_key=OPENAI_API_KEY)
except Exception as e:
    st.error(f"Error initializing AI models: {str(e)}")
    st.stop()

###############################################################################
#                            DATA PREPARATION                                 #
###############################################################################

def load_and_index_products():
    """Load Shopify CSV and create VectorStoreIndex with embeddings"""
    try:
        products_df = pd.read_csv("product.csv")
        
        # Validate required columns
        required_columns = ['Title', 'Body (HTML)', 'Variant Price', 'Image Src', 'Handle']
        missing = [col for col in required_columns if col not in products_df.columns]
        if missing:
            st.error(f"Missing required columns: {', '.join(missing)}")
            return None, None

        # Create nodes with metadata
        nodes = [
            TextNode(
                text=f"Product: {row['Title']}\nDescription: {row['Body (HTML)']}\nPrice: {row['Variant Price']}",
                metadata={
                    "title": row['Title'],
                    "price": row['Variant Price'],
                    "image_url": row['Image Src'],
                    "product_url": f"https://yourstore.com/products/{row['Handle']}",
                    "vendor": row.get('Vendor', ''),
                    "inventory": row.get('Variant Inventory Qty', 0)
                }
            )
            for _, row in products_df.iterrows()
        ]

        # Create index
        parser = SimpleNodeParser()
        nodes = parser.get_nodes_from_documents(nodes)
        return VectorStoreIndex(nodes), products_df
    
    except Exception as e:
        st.error(f"Error loading products: {str(e)}")
        return None, None

###############################################################################
#                          PRODUCT DISPLAY FUNCTION                           #
###############################################################################

def enhance_product_display(response_text: str) -> str:
    """Replace [PRODUCT] tags with styled cards"""
    try:
        pattern = r'\[PRODUCT\](.*?)\[\/PRODUCT\]'
        products = re.findall(pattern, response_text, re.IGNORECASE)
        
        for product_title in products:
            results = st.session_state.product_index.as_retriever().retrieve(product_title)
            if results:
                product = results[0].node.metadata
                card_html = f"""
                <div class="product-card">
                    <h4>{product['title']}</h4>
                    <img src="{product['image_url']}" width="100" style="max-width:100%; height:auto;">
                    <p>Price: ${product['price']}</p>
                    <p>Vendor: {product['vendor']}</p>
                    <a href="{product['product_url']}" target="_blank">
                        <button class="view-button">View Product</button>
                    </a>
                </div>
                """
                response_text = response_text.replace(f"[PRODUCT]{product_title}[/PRODUCT]", card_html)
        
        return response_text
    except Exception as e:
        st.error(f"Error displaying products: {str(e)}")
        return response_text

###############################################################################
#                                TOOLS                                        #
###############################################################################

def product_search_tool(query: str) -> str:
    """Search products using VectorStoreIndex"""
    try:
        retriever = st.session_state.product_index.as_retriever(similarity_top_k=3)
        results = retriever.retrieve(query)
        return "\n".join([f"[PRODUCT]{node.node.metadata['title']}[/PRODUCT] (${node.node.metadata['price']})" for node in results])
    except Exception as e:
        return f"Error searching products: {str(e)}"

def get_lowest_price_tool(query: str) -> str:
    """Find lowest priced products"""
    try:
        products = st.session_state.products_df.sort_values('Variant Price').head(3)
        return "\n".join([f"[PRODUCT]{row['Title']}[/PRODUCT] (${row['Variant Price']})" for _, row in products.iterrows()])
    except Exception as e:
        return f"Error finding lowest prices: {str(e)}"

###############################################################################
#                              INITIALIZATION                                 #
###############################################################################

def init_session():
    """Initialize session state"""
    try:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "product_index" not in st.session_state:
            st.session_state.product_index, st.session_state.products_df = load_and_index_products()
            if st.session_state.product_index is None:
                st.error("Failed to initialize product index")
                st.stop()

        if "agent" not in st.session_state:
            tools = [
                FunctionTool.from_defaults(fn=product_search_tool, name="product_search"),
                FunctionTool.from_defaults(fn=get_lowest_price_tool, name="lowest_price")
            ]

            st.session_state.agent = ReActAgent.from_tools(
                tools=tools,
                llm=Settings.llm,
                system_prompt="""
                You are an e-commerce assistant. Follow these rules:
                1. Always use tools for product queries
                2. Wrap product names in [PRODUCT][/PRODUCT] tags
                3. Mention prices and include images
                4. Keep responses concise but helpful
                """
            )
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")
        st.stop()

###############################################################################
#                                   MAIN                                      #
###############################################################################

def main():
    st.title("🛍️ Shopify Assistant")
    init_session()

    # Display chat history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"], unsafe_allow_html=True)

    # Handle input
    if prompt := st.chat_input("Ask about products..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        try:
            response = st.session_state.agent.chat(prompt)
            processed_response = enhance_product_display(response.response)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": processed_response
            })
            st.chat_message("assistant").markdown(processed_response, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
