# SmartKart Interaction Flow Outline (Button/Audio Focused)

**Core Concepts:**

*   **Modes:** The system will operate in distinct modes (Scanning, Item Scanned, Cart Review).
*   **Physical Buttons:** Assume dedicated physical buttons connected to the Raspberry Pi's GPIO pins (e.g., Select/Add, Info/Next, Back/Previous, Mode/Cart).
*   **Audio First:** Voice feedback is the primary way the system communicates state and information.
*   **Web UI:** Primarily for initial setup, viewing the camera feed/scan results visually, and potentially as a fallback or detailed view. The main *control* shifts to buttons.
*   **Backend Logic:** The Flask app manages state, processes button actions, handles the cart, and triggers speech.
*   **Button Listener:** A separate process/script on the Pi listens for GPIO button presses and sends requests to the Flask app.

**I. System States (Modes)**

1.  **Scanning Mode:**
    *   **Entry:** Default state on startup, after adding an item, after cancelling a scan, or exiting Cart Review.
    *   **Visuals (Web UI):** Shows live camera feed. Status: "Ready to Scan".
    *   **Audio:** Silent or optional subtle "ready" chime.
    *   **Functionality:** Backend continuously processes video frames for barcodes.
    *   **Button Actions:**
        *   `Mode/Cart` Button: Switch to Cart Review Mode.
        *   Other buttons: (Optional) Could trigger help message? Or do nothing.
    *   **Transition:** On barcode detected -> Item Scanned Mode.

2.  **Item Scanned Mode:**
    *   **Entry:** Barcode successfully detected and product looked up (found or not found).
    *   **Visuals (Web UI):** Update results area with Product Name/Brand (or "Not Found"). Highlight button functions?
    *   **Audio:** Immediately announce "Found [Product Name] by [Brand]." OR "Product not found for barcode [barcode]."
    *   **Functionality:** Holds the `last_scanned_product` data. Waits for button input.
    *   **Button Actions:**
        *   `Select/Add` Button: Add the item to the cart. Audio: "Added [Product Name] to cart." -> Transition to Scanning Mode. (If "Not Found", Audio: "Cannot add unknown product.")
        *   `Info/Next` Button: Announce Allergens. Audio: "Allergens: [List]" or "No known allergens listed." (Stays in Item Scanned Mode).
        *   `Back/Previous` Button: Discard scan result. Audio: "Scan cancelled." -> Transition to Scanning Mode.
        *   `Mode/Cart` Button: Switch to Cart Review Mode.
    *   **Transition:** Based on button press. Timeout? Maybe revert to Scanning Mode after X seconds? (Optional).

3.  **Cart Review Mode:**
    *   **Entry:** Pressing `Mode/Cart` button from Scanning or Item Scanned mode.
    *   **Visuals (Web UI):** Hide camera feed? Display numbered/highlighted list of items in cart. Show current item index / total count.
    *   **Audio:** On entry: "Cart View. [N] items. Item 1: [Name of Item 1]." (Announces first item).
    *   **Functionality:** Manages a list of items in the cart. Tracks the currently "selected" item index for navigation.
    *   **Button Actions:**
        *   `Select/Add` Button: Announce *Ingredients* for the currently selected item. Audio: "Ingredients: [List]" or "Ingredients not available." (Stays in Cart Review Mode).
        *   `Info/Next` Button: Move to next item in cart (wraps around). Audio: "Item [New Index]: [Item Name]." (Stays in Cart Review Mode).
        *   `Back/Previous` Button: Move to previous item in cart (wraps around). Audio: "Item [New Index]: [Item Name]." (Stays in Cart Review Mode).
        *   `Mode/Cart` Button: Exit Cart Review. Audio: "Exiting Cart View." -> Transition to Scanning Mode.
    *   **Transition:** `Mode/Cart` button exits.

**II. Backend Implementation (Flask App - `web_app.py`)**

1.  **State Management:**
    *   Maintain a global variable for the current mode (e.g., `current_mode = "SCANNING"`).
    *   Maintain an in-memory list for the cart (e.g., `shopping_cart = []`). Each item could be a dictionary like `last_scanned_product`.
    *   Maintain an index for the currently selected item in Cart Review mode (e.g., `cart_index = 0`).
2.  **New API Endpoints for Button Actions:**
    *   `/api/action/add_to_cart` (POST): If `current_mode == "ITEM_SCANNED"` and `last_scanned_product` is valid, add it to `shopping_cart`, trigger "Added..." speech, set `current_mode = "SCANNING"`.
    *   `/api/action/announce_allergens` (POST): If `current_mode == "ITEM_SCANNED"` and `last_scanned_product` is valid, trigger speech for allergens.
    *   `/api/action/announce_ingredients` (POST): If `current_mode == "CART_REVIEW"`, get item at `cart_index` from `shopping_cart`, trigger speech for ingredients.
    *   `/api/action/cart_next` (POST): If `current_mode == "CART_REVIEW"`, increment `cart_index` (handle wrapping), get item name, trigger speech for item name.
    *   `/api/action/cart_previous` (POST): If `current_mode == "CART_REVIEW"`, decrement `cart_index` (handle wrapping), get item name, trigger speech for item name.
    *   `/api/action/cancel_scan` (POST): If `current_mode == "ITEM_SCANNED"`, trigger "Scan cancelled" speech, set `current_mode = "SCANNING"`.
    *   `/api/action/enter_cart_view` (POST): Set `current_mode = "CART_REVIEW"`, reset `cart_index = 0` (or -1 if empty), trigger entry speech (incl. first item name if cart not empty).
    *   `/api/action/exit_cart_view` (POST): Trigger "Exiting..." speech, set `current_mode = "SCANNING"`.
    *   `/api/state` (GET): (Optional) Endpoint for the button listener to query the current mode.
3.  **Modify Existing Logic:**
    *   `generate_frames`: When barcode detected, set `current_mode = "ITEM_SCANNED"`, update `last_scanned_product`, trigger initial "Found..." speech. *Don't* trigger allergen/ingredient speech here.
    *   `SpeechManager`: Needs to handle potentially longer ingredient lists gracefully. Maybe break them down? (Future improvement).
4.  **Cart Data API:**
    *   `/api/cart/items` (GET): Returns the current content of `shopping_cart` (for potential display in Web UI).

**III. Hardware Button Listener (Separate Script - `button_handler.py`?)**

1.  **Libraries:** Use `RPi.GPIO` or `gpiozero`.
2.  **Setup:** Configure GPIO pins for the buttons (pull-up or pull-down resistors).
3.  **Debouncing:** Implement software debouncing for reliable press detection.
4.  **Action Mapping:**
    *   On button press:
        *   (Optional) Query Flask app state: `requests.get('http://localhost:5000/api/state')`.
        *   Determine which API endpoint to call based on the button pressed and the current state (e.g., if state is "SCANNING" and Button 4 is pressed, call `/api/action/enter_cart_view`).
        *   Send POST request: `requests.post('http://localhost:5000/api/action/...')`.
5.  **Run as Service:** This script needs to run persistently in the background on the Pi.

**IV. Web UI (`scanner.html`, new `cart.html`?)**

1.  **Scanner Page:** Primarily shows video feed and the `last_scanned_product` details. Could potentially highlight active button functions based on the current mode (fetched via polling?).
2.  **Cart Page (Optional):** Could add a separate `/cart` route/template that displays the items fetched from `/api/cart/items`. Useful for visual review but not essential for the button-driven flow.
3.  **Settings Page:** Stays as is (minimal audio settings now).

**Considerations:**

*   **Persistence:** The in-memory cart will be lost on server restart. Saving/loading the cart to/from a JSON file would be a good improvement.
*   **Error Handling:** More robust error handling (e.g., what if API lookup fails? What if buttons are pressed in the wrong mode?).
*   **Removing Items:** Adding a "Remove Item" function in Cart Review mode would require careful button mapping (e.g., long-press, combo press, or an additional button).
*   **Clearing Cart:** A way to clear the entire cart might be needed (perhaps via Settings page or another button combo). 