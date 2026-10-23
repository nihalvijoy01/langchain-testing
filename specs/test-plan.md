# Test Plan for Cart Functionality

## Application Overview

This test plan focuses on verifying the functionality of adding products to the cart on the **Automation Exercise** e-commerce website. The scenario covers the **happy path** for a user adding a product to the cart, ensuring the core functionality works as expected.

## Test Scenarios

### 1. Cart Functionality

**Seed:** `tests/seed.spec.ts`

#### 1.1. Add a Product to the Cart

**File:** `tests/cart/add-product-to-cart.spec.ts`

**Steps:**
  1. Navigate to the homepage at `https://automationexercise.com/`.
    - expect: The homepage loads successfully, displaying the "Features Items" section.
  2. Scroll to the "Features Items" section and click the "Add to cart" button for the first product listed (e.g., "Blue Top").
    - expect: A confirmation modal appears with the message: "View Cart" and "Continue Shopping" buttons.
  3. Click the "View Cart" button in the modal.
    - expect: The cart page loads, displaying the selected product ("Blue Top") with the correct product name, price, quantity (default: 1), and total price.
  4. Validate the cart contents by verifying the product details (name, price, quantity, and total).
    - expect: The cart displays the correct product details, confirming successful addition.
