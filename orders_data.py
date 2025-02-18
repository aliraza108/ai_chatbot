# Import necessary modules
import os
from dotenv import load_dotenv
import shopify
from notes import note_engine
from llama_index.core.tools import FunctionTool

# Load environment variables
load_dotenv()

# Set up Shopify API credentials and site URL
shopify.ShopifyResource.set_site(
    f"https://{os.getenv('SHOPIFY_API_KEY')}:{os.getenv('SHOPIFY_ACCESS_TOKEN')}@{os.getenv('SHOPIFY_SHOP_URL')}/admin/api/2025-01"
)

# Function to query Shopify orders
def query_shopify_orders(order_id: str = None) -> str:
    """Retrieve real-time order data from Shopify store."""
    try:
        # Fetch orders from Shopify
        if order_id:
            # Fetch a specific order by ID
            order = shopify.Order.find(order_id)
            if not order:
                return f"No order found with ID: {order_id}."
            
            # Extract order information
            order_info = [
                f"Order ID: {order.id}",
                f"Customer: {order.customer.first_name} {order.customer.last_name} (ID: {order.customer.id})",
                f"Status: {order.financial_status}",
                f"Amount: {order.total_price}",
                f"Products: {', '.join([item.title for item in order.line_items])}",  # List of product names
                f"Total Items: {sum(item.quantity for item in order.line_items)}",  # Sum of all item quantities
                f"Notes: {order.note or 'N/A'}",
                f"Delivery Status: {order.fulfillment_status or 'N/A'}",
                f"Created At: {order.created_at}"
            ]
            return "\n".join(order_info)
        
        else:
            # Fetch all orders
            orders = shopify.Order.find()
            if not orders:
                return "No orders found in store."
            
            response_data = []
            for order in orders:
                order_info = [
                    f"Order ID: {order.id}",
                    f"Customer: {order.customer.first_name} {order.customer.last_name} (ID: {order.customer.id})",
                    f"Status: {order.financial_status}",
                    f"Amount: {order.total_price}",
                    f"Products: {', '.join([item.title for item in order.line_items])}",  # List of product names
                    f"Total Items: {sum(item.quantity for item in order.line_items)}",  # Sum of all item quantities
                    f"Notes: {order.note or 'N/A'}",
                    f"Delivery Status: {order.fulfillment_status or 'N/A'}",
                    f"Created At: {order.created_at}"
                ]
                response_data.append("\n".join(order_info))
            
            return "\n".join(response_data)
    
    except Exception as e:
        return f"Error accessing Shopify: {str(e)}"

# Create Shopify query tool
shopify_order_tool = FunctionTool.from_defaults(
    fn=query_shopify_orders,
    name="shopify_products",
    description=(
        "Access real-time Order data including, order status, amount, customer information, delivery status, notes, and total items. "
        "Easily manage and analyze order data in one place."
    )
)