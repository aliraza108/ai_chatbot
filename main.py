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
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.schema import TextNode

# Load environment variables
load_dotenv()

# Initialize OpenAI API key
OPENAI_API_KEY = "sk-proj-..."  # Replace with your key

###############################################################################
#                            DATA PREPARATION                                 #
###############################################################################

def load_and_index_products():
    """Load Shopify CSV and create VectorStoreIndex with embeddings"""
    # Load CSV data
    products_df = pd.read_csv("product.csv")
    
    # Create nodes with metadata
    nodes = []
    for _, row in products_df.iterrows():
        node = TextNode(
            text=f"Product: {row['Title']}\nDescription: {row['Body (HTML)']}\nPrice: {row['Variant Price']}",
            metadata={
                "title": row['Title'],
                "price": row['Variant Price'],
                "image_url": row['Image Src'],
                "product_url": f"https://yourstore.com/products/{row['Handle']}",  # Update with your store URL
                "vendor": row['Vendor'],
                "type": row['Type'],
                "tags": row['Tags'],
                "inventory": row['Variant Inventory Qty']
            }
        )
        nodes.append(node)
    
    # Create index
    parser = SimpleNodeParser()
    nodes = parser.get_nodes_from_documents(nodes)
    return VectorStoreIndex(nodes), products_df

###############################################################################
#                          PRODUCT DISPLAY FUNCTION                           #
###############################################################################

def enhance_product_display(response_text: str) -> str:
    """Replace [PRODUCT] tags with styled cards"""
    pattern = r'\[PRODUCT\](.*?)\[\/PRODUCT\]'
    products = re.findall(pattern, response_text, re.IGNORECASE)
    
    for product_title in products:
        # Get product info from index
        results = st.session_state.product_index.as_retriever().retrieve(product_title)
        if results:
            product = results[0].node.metadata
            card_html = f"""
            <div class="product-card">
                <h4>{product['title']}</h4>
                <img src="{product['image_url']}" width="100" style="max-width:100%; height:auto;">
                <p>Price: ${product['price']}</p>
                <p>Vendor: {product['vendor']}</p>
                <p>Stock: {product['inventory']}</p>
                <a href="{product['product_url']}" target="_blank">
                    <button class="view-button">View Product</button>
                </a>
            </div>
            """
            response_text = response_text.replace(f"[PRODUCT]{product_title}[/PRODUCT]", card_html)
    
    return response_html

###############################################################################
#                                TOOLS                                        #
###############################################################################

def product_search_tool(query: str) -> str:
    """Search products using VectorStoreIndex"""
    retriever = st.session_state.product_index.as_retriever(similarity_top_k=3)
    results = retriever.retrieve(query)
    
    if not results:
        return "No products found."
    
    response = []
    for node in results:
        metadata = node.node.metadata
        response.append(f"[PRODUCT]{metadata['title']}[/PRODUCT] (${metadata['price']})")
    
    return "\n".join(response)

def get_lowest_price_tool(query: str) -> str:
    """Find lowest priced products"""
    products = st.session_state.products_df.sort_values('Variant Price').head(3)
    return "\n".join([f"[PRODUCT]{row['Title']}[/PRODUCT] (${row['Variant Price']})" for _, row in products.iterrows()])

def get_inventory_status(query: str) -> str:
    """Check product inventory status"""
    product = st.session_state.products_df[st.session_state.products_df['Title'].str.contains(query, case=False)]
    if not product.empty:
        return f"Inventory status for {product.iloc[0]['Title']}: {product.iloc[0]['Variant Inventory Qty']} in stock"
    return "Product not found"

###############################################################################
#                              INITIALIZATION                                 #
###############################################################################

def apply_styles():
    """Add custom CSS styles"""
    st.markdown("""
    <style>
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background: #f8f9fa;
    }
    .view-button {
        background: #4CAF50;
        color: white;
        padding: 6px 12px;
        border: none;
        border-radius: 4px;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

def init_session():
    """Initialize session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "product_index" not in st.session_state:
        st.session_state.product_index, st.session_state.products_df = load_and_index_products()

    if "agent" not in st.session_state:
        # Create tools
        tools = [
            FunctionTool.from_defaults(
                fn=product_search_tool,
                name="product_search",
                description="Search products by title, description, or features"
            ),
            FunctionTool.from_defaults(
                fn=get_lowest_price_tool,
                name="lowest_price",
                description="Find the lowest priced products in the catalog"
            ),
            FunctionTool.from_defaults(
                fn=get_inventory_status,
                name="inventory_check",
                description="Check inventory status for specific products"
            )
        ]

        # Configure LLM
        Settings.llm = OpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            temperature=0.1
        )

        # Create agent
        st.session_state.agent = ReActAgent.from_tools(
            tools=tools,
            system_prompt="""
            You are an e-commerce assistant for a Shopify store. Follow these rules:
            1. ALWAYS use tools for product queries
            2. Wrap product names in [PRODUCT][/PRODUCT] tags
            3. Mention prices and inventory when available
            4. For price comparisons, use lowest_price tool
            5. Always include product images and buttons
            6. Keep responses concise but helpful
            7. Use inventory_check tool for stock inquiries
            """
        )

###############################################################################
#                                   MAIN                                      #
###############################################################################

def main():
    st.title("🛍️ Shopify Product Assistant")
    apply_styles()
    init_session()

    # Display chat history
    for msg in st.session_state.messages:
        role = "assistant" if msg["role"] == "assistant" else "user"
        st.chat_message(role).markdown(msg["content"], unsafe_allow_html=True)

    # Handle input
    if prompt := st.chat_input("Ask about products, prices, or inventory..."):
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
