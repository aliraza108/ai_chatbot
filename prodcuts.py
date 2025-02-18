# Import necessary modules
import os
from dotenv import load_dotenv
import shopify
from notes import note_engine
from llama_index.core.tools import FunctionTool

# Load environment variables
load_dotenv()

# Configure Shopify API
shopify.ShopifyResource.set_site(
    f"https://{os.getenv('SHOPIFY_API_KEY')}:{os.getenv('SHOPIFY_ACCESS_TOKEN')}@{os.getenv('SHOPIFY_SHOP_URL')}/admin/api/2025-01"
)

# Function to query Shopify products
def query_shopify_products(query: str) -> str:
    """Retrieve real-time product data from Shopify store."""
    try:
        # Fetch products from Shopify
        products = shopify.Product.find()
        if not products:
            return "No products found in store."
        
        response_data = []
        for product in products:
            # Extract product information
            product_info = [
                f"Product: {product.title}",
                f"Description: {product.body_html or 'N/A'}",
                f"Prices: {', '.join([v.price for v in product.variants])}",
                f"URL: https://{os.getenv('SHOPIFY_SHOP_URL')}/products/{product.handle}",
                "---"
            ]
            response_data.append("\n".join(product_info))
        
        return "\n".join(response_data)
    
    except Exception as e:
        return f"Error accessing Shopify: {str(e)}"

# Create Shopify query tool
shopify_tool = FunctionTool.from_defaults(
    fn=query_shopify_products,
    name="shopify_products",
    description="Access real-time product data including names, descriptions, prices, and URLs of products."
)