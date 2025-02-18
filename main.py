

# main.py
import streamlit as st
import os
import shopify
import re
from dotenv import load_dotenv
from notes import note_engine
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.llms import openai
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Configure Shopify API
def configure_shopify():
    shopify.ShopifyResource.set_site(
        f"https://{os.getenv('SHOPIFY_API_KEY')}:{os.getenv('SHOPIFY_ACCESS_TOKEN')}"
        f"@{os.getenv('SHOPIFY_SHOP_URL')}/admin/api/2024-01"
    )

def append_product_thumbnail(response, image_width: int = 200) -> str:
    """
    Improved version to handle multiple products, different image sizes, and "View Product" buttons.
    """
    if not isinstance(response, str):
        response = str(response)

    # Check for existing images using a more robust pattern
    if re.search(r'<img[^>]*>', response):
        return response

    # Find all potential product titles (including markdown bold formats)
    matches = re.finditer(r'(\*\*)?(?P<title>[^\n*]+?)(\*\*)?( - Price|:|\n|$)', response, re.IGNORECASE)

    try:
        products = shopify.Product.find()
        updated_response = response
        
        for match in matches:
            product_title = match.group('title').strip('"').strip()
            
            for product in products:
                # Fuzzy match product titles
                clean_product_title = product.title.strip().lower()
                clean_query = product_title.lower()
                
                if clean_query in clean_product_title or clean_product_title in clean_query:
                    if product.images:
                        first_image = product.images[0].src
                        # Build the product URL
                        product_url = f"https://{os.getenv('SHOPIFY_SHOP_URL')}/products/{product.handle}"
                        # Add responsive image sizing and "View Product" button
                        image_html = f'''
                        <br>
                        <img src="{first_image}" 
                            width="{image_width}" 
                            style="max-width:100%; height:auto; border-radius:5px;"
                            alt="{product.title} thumbnail"
                        >
                        <br>
                        <a href="{product_url}" target="_blank">
                            <button style="
                                background-color: #4CAF50;
                                color: white;
                                padding: 8px 16px;
                                border: none;
                                border-radius: 5px;
                                cursor: pointer;
                                margin-top: 8px;
                            ">
                                View Product
                            </button>
                        </a>
                        <br>
                        '''
                        # Replace only the first occurrence of this title
                        updated_response = updated_response.replace(
                            match.group(0), 
                            f"{match.group(0)}{image_html}", 
                            1
                        )
                        break
        
        return updated_response

    except Exception as e:
        print(f"Error in image insertion: {e}")
        return response

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        configure_shopify()
        
        def query_shopify_products(query: str) -> str:
            try:
                products = shopify.Product.find()
                response_data = []
                for product in products:
                    # Build a tiny thumbnail image if available
                    image_html = ""
                    if hasattr(product, 'images') and product.images:
                        first_image = product.images[0]
                        image_src = getattr(first_image, 'src', None) or first_image.get('src', '')
                        if image_src:
                            # Using 200px width; change to 300px if desired
                            image_html = f'<br><img src="{image_src}" width="200" style="max-width:100%; border-radius: 5px;" alt="{product.title} thumbnail"/><br>'
                    
                    product_info = f"""
                    **{product.title}**  
                    {image_html}
                    {product.body_html or 'No description provided.'}  
                    Prices: {', '.join([v.price for v in product.variants])}  
                    [View Product](https://{os.getenv('SHOPIFY_SHOP_URL')}/products/{product.handle})
                    """
                    response_data.append(product_info)
                return "\n\n".join(response_data)
            except Exception as e:
                return f"Error: {str(e)}"

        shopify_tool = FunctionTool.from_defaults(
            fn=query_shopify_products,
            name="shopify_products",
            description="Access real-time product data including names, descriptions, prices, URLs, and product thumbnails."
        )

        llm = openai.OpenAI(model="gpt-3.5-turbo-0125")
        st.session_state.agent = ReActAgent.from_tools(
            tools=[note_engine, shopify_tool],
            llm=llm,
            verbose=False,
            context="You're a Shopify assistant providing product info and taking notes. "
                    "When referencing a product, include a thumbnail image and a 'View Product' button."
        )

def apply_custom_styles():
    st.markdown("""
    <style>
    /* Hide rerun, deploy, and settings options */
    .stDeployButton { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Custom colors and rounded corners */
    .stChatMessage {
        padding: 1rem;
        border-radius: 1rem;
        margin: 1rem 0;
    }
    .stChatMessage.user {
        background-color: #003166;
        color: white;
    }
    .stChatMessage.assistant {
        background-color: #ff9b00;
        color: black;
    }
    [data-testid="stChatMessageContent"] p {
        font-size: 1.1rem;
    }
    /* Ensure images are responsive and look good on both desktop and mobile */
    .stChatMessage img {
        max-width: 300px;
        height: auto;
        margin-top: 0.5rem;
    }
    /* Style for the "View Product" button */
    .stChatMessage a button {
        background-color: #4CAF50;
        color: white;
        padding: 8px 16px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        margin-top: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🛍️ Ali's Shop Assistant")
    
    init_session()
    apply_custom_styles()

    # Display chat messages with HTML enabled
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🧑" if message["role"] == "user" else "🤖"):
            st.markdown(message["content"], unsafe_allow_html=True)

    # Handle user input
    if prompt := st.chat_input("Ask about products or leave a note..."):
        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt, unsafe_allow_html=True)

        # Get agent response and post-process it to inject a thumbnail if applicable
        try:
            with st.chat_message("assistant", avatar="🤖"):
                response = st.session_state.agent.query(prompt)
                # Append thumbnail image and "View Product" button if a product title is detected
                response = append_product_thumbnail(response, image_width=100)  # Set to 100px or 200px as needed
                st.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")

if __name__ == "__main__":
    main()