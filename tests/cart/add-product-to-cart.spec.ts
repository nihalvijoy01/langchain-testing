// spec: specs/test-plan.md
// seed: tests/seed.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Cart Functionality', () => {
  test('Add a Product to the Cart', async ({ page }) => {
    // 1. Navigate to the homepage at `https://automationexercise.com/`.
    // expect: The homepage loads successfully, displaying the "Features Items" section.
    await page.goto('https://automationexercise.com/');
    await expect(page.getByRole('heading', { name: 'Features Items' })).toBeVisible();

    // 2. Scroll to the "Features Items" section and click the "Add to cart" button for the first product listed (e.g., "Blue Top").
    // expect: A confirmation modal appears with the message: "View Cart" and "Continue Shopping" buttons.
    await page.getByText('Add to cart').first().click();
    await expect(page.getByRole('link', { name: 'View Cart' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Continue Shopping' })).toBeVisible();

    // 3. Click the "View Cart" button in the modal.
    // expect: The cart page loads, displaying the selected product ("Blue Top") with the correct product name, price, quantity (default: 1), and total price.
    await page.locator('a:has-text("View Cart")').click();
    await expect(page.getByRole('cell', { name: 'Blue Top Women > Tops' })).toBeVisible();
    
    // 4. Validate the cart contents by verifying the product details (name, price, quantity, and total).
    // expect: The cart displays the correct product details, confirming successful addition.
    const priceCell = page.getByRole('cell', { name: 'Rs. 500' });
    await expect(priceCell.first()).toBeVisible();
    await expect(page.getByRole('button', { name: '1' })).toBeVisible();
    await expect(priceCell.last()).toBeVisible();
  });
});