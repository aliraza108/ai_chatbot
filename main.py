import os
import re
import warnings
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

# 1) LlamaIndex imports (pinned to llama-index==0.5.6 in your requirements)
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.llms import OpenAI as LLMOpenAI

# 2) Load environment variables
load_dotenv()

# 3) Use your OpenAI API key (hard-coded as requested)
OPENAI_API_KEY = (
    "sk-proj-"
    + "p2dN0_oztdhFKtMjji9f5DGI7XQPFEORui43AF1arpd57VAdcEc2sHI77mSk5YX74uqgYIQYAwT3BlbkFJ_Bokz-n5mwr6coif3oieLYHu-6Xz5hxawV2mlKXtpTAOiyXiKWm6jtv5e7FOLlew8fSYFiU68A"
)

###############################################################################
#                               FAKE DATA                                     #
###############################################################################

# Some fake personal info, keyed by user ID or email
FAKE_PERSONAL_DATA = {
    "john@example.com": {
        "name": "John Doe",
        "email": "john@example.com",
        "loyalty_points": 1200,
        "preferred_language": "English",
    },
    "jane@example.com": {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "loyalty_points": 300,
        "preferred_language": "French",
    },
}

# Some fake conversation history, keyed by user ID or email
FAKE_CONVERSATION_HISTORY = {
    "john@example.com": [
        "User asked about shipping times on 2025-01-10",
        "User asked about returns policy on 2025-01-15",
    ],
    "jane@example.com": [
        "User asked about discount codes on 2025-01-20",
    ],
}

###############################################################################
#                         PRODUCT DISPLAY FUNCTION                            #
###############################################################################

def enhance_product_display(response_text: str, products_df: pd.DataFrame) -> str:
    """
    Replace <h3>product_title</h3> in the response with an HTML card containing
    the product title, image, price, and a "View Product" button.
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
                <img src="{product['image_url']}" 
                     width="100" 
                     style="max-width:100%; height:auto;"
                     alt="{product['title']}">
                <p>Price: ${product['price']}</p>
                <a href="{product['product_url']}" target="_blank">
                    <button>View Product</button>
                </a>
            </div>
            """
            response_text = response_text[:match.start()] + card_html + response_text[match.end():]
    return response_text

###############################################################################
#                                TOOLS                                        #
###############################################################################

def get_product_data(query: str) -> str:
    """
    1) This is the 'product data tool'.
    2) Takes a query and returns up to 3 matching product titles, each wrapped in <h3>.
       For simplicity, we just return the first 3 products in the DataFrame or
       do a basic substring match on 'title'.
    """
    products_df = st.session_state.products_df
    query_lower = query.lower()
    # Filter by substring match in 'title' (basic example)
    matched = products_df[products_df['title'].str.lower().str.contains(query_lower)]
    # If no match, return a fallback
    if matched.empty:
        return "No matching products found."
    # Limit to 3
    matched = matched.head(3)
    # Return titles wrapped in <h3> tags
    return "\n".join([f"<h3>{row['title']}</h3>" for _, row in matched.iterrows()])


def get_personal_info(query: str) -> str:
    """
    1) This is the 'personal info tool'.
    2) Takes an email or user ID as a query, returns user info from FAKE_PERSONAL_DATA.
    """
    user_data = FAKE_PERSONAL_DATA.get(query.lower())
    if not user_data:
        return "No personal info found for that user."
    return (
        f"Name: {user_data['name']}\n"
        f"Email: {user_data['email']}\n"
        f"Loyalty Points: {user_data['loyalty_points']}\n"
        f"Preferred Language: {user_data['preferred_language']}"
    )


def get_conversation_history(query: str) -> str:
    """
    1) This is the 'conversation tool'.
    2) Takes an email or user ID as a query, returns conversation logs from FAKE_CONVERSATION_HISTORY.
    """
    history = FAKE_CONVERSATION_HISTORY.get(query.lower())
    if not history:
        return "No conversation history found for that user."
    return "Conversation history:\n" + "\n".join(history)

###############################################################################
#                              INITIALIZATION                                 #
###############################################################################

def apply_styles():
    """Apply CSS styling for product cards, chat messages, and buttons."""
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
    1) Initialize chat messages.
    2) Load product CSV (e.g. product.csv).
    3) Create a ReActAgent with multiple tools (product data, personal info, conversation).
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Load product data from CSV if not already loaded
    if "products_df" not in st.session_state:
        csv_path = os.path.join("product.csv")  # or wherever your file is
        df = pd.read_csv(csv_path)

        # Make sure these columns exist in your CSV or rename them accordingly
        # e.g., "Title", "Variant Price", "Image Src", "Handle"
        # Then map them to "title", "price", "image_url", "product_url"
        # For example:
        # df["title"] = df["Title"]
        # df["price"] = df["Variant Price"]
        # df["image_url"] = df["Image Src"]
        # df["product_url"] = "https://yourstore.myshopify.com/products/" + df["Handle"]

        # For demonstration, let's assume your CSV already has the columns below:
        st.session_state.products_df = df

    # Create the ReActAgent with your 3 tools
    if "agent" not in st.session_state:
        product_tool = FunctionTool.from_defaults(
            fn=get_product_data,
            name="product_data_tool",
            description="Retrieve up to 3 matching product titles from the product inventory"
        )
        personal_tool = FunctionTool.from_defaults(
            fn=get_personal_info,
            name="personal_info_tool",
            description="Retrieve personal info for a user (by email)"
        )
        convo_tool = FunctionTool.from_defaults(
            fn=get_conversation_history,
            name="conversation_tool",
            description="Retrieve conversation history for a user (by email)"
        )

        # Create LLM
        llm = LLMOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)

        # Create the ReActAgent with the tools
        st.session_state.agent = ReActAgent.from_tools(
            tools=[product_tool, personal_tool, convo_tool],
            llm=llm,
            verbose=False,
            # Provide some context or rules for the agent
            context="""
            You are a helpful e-commerce support agent. You have these tools:
            1) product_data_tool - for product data
            2) personal_info_tool - for user personal info
            3) conversation_tool - for user conversation history

            When the user asks about products, you can call product_data_tool.
            When the user asks about a specific user's info or conversation history, you can call the relevant tool.

            Return product titles wrapped in <h3> tags so the system can render them.
            Keep your responses helpful and concise.
            """
        )

###############################################################################
#                                   MAIN                                      #
###############################################################################

def main():
    st.title("E-commerce Support Chatbot")
    apply_styles()
    init_session()

    # Display existing chat messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").markdown(msg["content"])
        else:
            st.chat_message("assistant").markdown(msg["content"], unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("Ask me anything about products or your account..."):
        # Store user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        try:
            # Query the ReActAgent
            response = st.session_state.agent.query(prompt)
            # Enhance product display if <h3> tags are present
            processed_response = enhance_product_display(response.response, st.session_state.products_df)

            # Display assistant message
            st.chat_message("assistant").markdown(processed_response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": processed_response})

        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
