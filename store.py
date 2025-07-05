import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import json
import os

# Load Users from JSON File
def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}

# Save Users to JSON File
def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# Load Store Items from JSON File
# Load Store Items from JSON File
def load_store_items():
    if os.path.exists("store.json"):
        with open("store.json", "r") as f:
            return json.load(f)
    else:
        # Default store items if the file doesn't exist
        default_items = [
            {"name": "Figit Toy", "price": 25.0},
            {"name": "Glave", "price": 10.0}
        ]
        with open("store.json", "w") as f:
            json.dump(default_items, f, indent=4)  # Save default items to store.json
        return default_items

# Save Store Items to JSON File
def save_store_items(items):
    with open("store.json", "w") as f:
        json.dump(items, f, indent=4)


# Validate User Credentials and Admin Privileges
def validate_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        # Check if the user is an admin
        is_admin = users[username].get("is_admin", False)
        return True, users[username], is_admin
    return False, "Invalid username or password", False

# Create New User
def create_user(username, password):
    users = load_users()
    if username in users:
        return False, "Username already exists."
    
    # Make a specific user an admin by checking the username
    if username == "admin_user":
        is_admin = True
    else:
        is_admin = False

    users[username] = {
        "password": password,
        "balance": 100.0,
        "history": [],
        "is_admin": is_admin
    }
    save_users(users)
    return True, "Account created."

# ----- LOGIN AND SHOP GUI -----
class LoginWindow:
    def __init__(self, root):
        self.root = root
        root.title("Login")
        tk.Label(root, text="Username:").pack()
        self.username_entry = tk.Entry(root)
        self.username_entry.pack()

        tk.Label(root, text="Password:").pack()
        self.password_entry = tk.Entry(root, show="*")
        self.password_entry.pack()

        tk.Button(root, text="Login", command=self.login).pack(pady=5)
        tk.Button(root, text="Register", command=self.register).pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        valid, data, is_admin = validate_user(username, password)
        
        if valid:
            self.root.destroy()
            if is_admin:  # Only give access to Admin Panel if user is an admin
                AdminPanel(username)
            else:
                ShopGUI(username)
        else:
            messagebox.showerror("Error", data)

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        success, msg = create_user(username, password)
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)

# ----- SHOP GUI -----
class ShopGUI:
    def __init__(self, username):
        self.window = tk.Tk()
        self.window.title(f"Welcome, {username}")
        self.username = username
        self.user_data = load_users()[username]
        self.items = load_store_items()
        self.cart = []

        tk.Label(self.window, text=f"Balance: ${self.user_data['balance']:.2f}", font=("Arial", 14)).pack(pady=10)

        self.cart_label = tk.Label(self.window, text="Shopping Cart (Empty)", font=("Arial", 12))
        self.cart_label.pack(pady=5)

        for item in self.items:
            self.create_item_button(item)

        tk.Button(self.window, text="Checkout", command=self.checkout).pack(pady=10)
        tk.Button(self.window, text="View Transaction History", command=self.view_transaction_history).pack(pady=5)
        tk.Button(self.window, text="Toggle Dark Mode", command=self.toggle_theme).pack(pady=5)
        tk.Button(self.window, text="Logout", command=self.logout).pack(pady=5)

        self.window.mainloop()

    def create_item_button(self, item):
        button = tk.Button(self.window, text=f"{item['name']} - ${item['price']:.2f}",
                           command=lambda: self.add_to_cart(item))
        button.pack(pady=2)

    def add_to_cart(self, item):
        self.cart.append(item)
        self.update_cart_label()

    def update_cart_label(self):
        if self.cart:
            cart_items = ", ".join([item['name'] for item in self.cart])
            self.cart_label.config(text=f"Shopping Cart: {cart_items}")
        else:
            self.cart_label.config(text="Shopping Cart (Empty)")

    def checkout(self):
        total = sum([item['price'] for item in self.cart])
        if self.user_data['balance'] >= total:
            # Deduct total price from the balance
            self.user_data['balance'] -= total

            # Record each item in the transaction history
            for item in self.cart:
                self.user_data['history'].append(f"Bought {item['name']} for ${item['price']:.2f}")

            # Update the balance display
            self.balance_label = tk.Label(self.window, text=f"Balance: ${self.user_data['balance']:.2f}", font=("Arial", 14))
            self.balance_label.pack(pady=10)

            # Save updated data
            self.save()

            # Clear cart
            self.cart = []
            self.update_cart_label()

            messagebox.showinfo("Purchase Complete", f"Total: ${total:.2f}")
        else:
            messagebox.showwarning("Insufficient Funds", "You don't have enough funds for this purchase.")

    def save(self):
        users = load_users()
        users[self.username] = self.user_data
        save_users(users)

    def view_transaction_history(self):
        """View the transaction history of the current user."""
        history = self.user_data['history']
        if history:
            history_str = "\n".join(history)
        else:
            history_str = "No transactions yet."

        history_window = tk.Toplevel(self.window)
        history_window.title("Transaction History")

        history_text = tk.Text(history_window, height=10, width=50)
        history_text.pack(padx=10, pady=10)
        history_text.insert(tk.END, history_str)
        history_text.config(state="disabled")

    def toggle_theme(self):
        """Toggle between light and dark theme."""
        if self.window.option_get('theme', 'light') == 'light':
            self.window.tk_setPalette(background='white', foreground='black')
            self.window.option_add('*Button.background', 'f0f0f0')
            self.window.option_add('*Button.foreground', 'black')
            self.window.option_add('*Button.activeBackground', 'd3d3d3')
            self.window.option_add('*Button.activeForeground', 'black')
            self.window.option_add('*Label.foreground', 'black')
            self.window.option_add('*Label.background', 'white')
            self.window.option_add('*Text.background', 'white')
            self.window.option_add('*Text.foreground', '#666666')
            self.window.option_add('*TButton.style', 'dark')
            self.window.option_add('theme', 'light')
        else:
            self.window.tk_setPalette(background='#2c2c2c', foreground='white')
            self.window.option_add('*Button.background', '#4b4b4b')
            self.window.option_add('*Button.foreground', 'white')
            self.window.option_add('*Button.activeBackground', '#666666')
            self.window.option_add('*Button.activeForeground', 'white')
            self.window.option_add('*Label.foreground', 'white')
            self.window.option_add('*Label.background', 'black')
            self.window.option_add('*Text.background', 'black')
            self.window.option_add('*Text.foreground', 'white')
            self.window.option_add('theme', 'dark')

    def logout(self):
        self.window.destroy()
        root = tk.Tk()
        LoginWindow(root)
        root.mainloop()

# ----- ADMIN PANEL -----
class AdminPanel:
    def __init__(self, username):
        self.window = tk.Tk()
        self.window.title(f"Admin Panel - {username}")
        self.users = load_users()
        self.items = load_store_items()

        tk.Label(self.window, text="All User Accounts", font=("Arial", 14, "bold")).pack(pady=5)
        self.user_list = scrolledtext.ScrolledText(self.window, width=50, height=15)
        self.user_list.pack()
        self.refresh_user_list()

        # View Transaction History button
        tk.Button(self.window, text="View User Transaction History", command=self.view_user_history).pack(pady=5)
        tk.Button(self.window, text="Add Funds to User", command=self.add_funds).pack(pady=5)
        tk.Button(self.window, text="Delete User", command=self.delete_user).pack(pady=5)
        tk.Button(self.window, text="Manage Store Items", command=self.manage_store).pack(pady=5)

        self.window.mainloop()

    def refresh_user_list(self):
        self.user_list.config(state='normal')
        self.user_list.delete(1.0, tk.END)
        for username, data in self.users.items():
            self.user_list.insert(tk.END, f"{username} - Balance: ${data['balance']:.2f} - Admin: {data.get('is_admin', False)}\n")
        self.user_list.config(state='disabled')

    def view_user_history(self):
        """Allow the admin to view transaction history for any user."""
        user = simpledialog.askstring("User", "Enter username to view history:")
        if user in self.users:
            history = self.users[user]['history']
            if history:
                history_str = "\n".join(history)
            else:
                history_str = "No transactions yet."

            history_window = tk.Toplevel(self.window)
            history_window.title(f"Transaction History - {user}")

            history_text = tk.Text(history_window, height=10, width=50)
            history_text.pack(padx=10, pady=10)
            history_text.insert(tk.END, history_str)
            history_text.config(state="disabled")
        else:
            messagebox.showerror("Error", "User not found.")

    def add_funds(self):
        """Add funds to a user's account."""
        username = simpledialog.askstring("User", "Enter username to add funds:")
        if username in self.users:
            amount = simpledialog.askfloat("Add Funds", f"Enter amount to add to {username}'s account:")
            if amount:
                self.users[username]['balance'] += amount
                save_users(self.users)
                messagebox.showinfo("Success", f"Added ${amount:.2f} to {username}'s account.")
            else:
                messagebox.showerror("Error", "Invalid amount.")
        else:
            messagebox.showerror("Error", "User not found.")

    def delete_user(self):
        """Delete a user from the system."""
        username = simpledialog.askstring("Delete User", "Enter username to delete:")
        if username in self.users:
            del self.users[username]
            save_users(self.users)
            messagebox.showinfo("Success", f"{username} has been deleted.")
        else:
            messagebox.showerror("Error", "User not found.")

    def manage_store(self):
        """Allow the admin to manage the store items."""
        store_window = tk.Toplevel(self.window)
        store_window.title("Manage Store Items")

        # List of current store items
        item_listbox = tk.Listbox(store_window, width=50, height=10)
        item_listbox.pack(padx=10, pady=10)
        for item in self.items:
            item_listbox.insert(tk.END, f"{item['name']} - ${item['price']:.2f}")

        # Buttons to manage store items
        tk.Button(store_window, text="Add Item", command=lambda: self.add_item(store_window)).pack(pady=5)
        tk.Button(store_window, text="Remove Item", command=lambda: self.remove_item(item_listbox)).pack(pady=5)
        tk.Button(store_window, text="Edit Item", command=lambda: self.edit_item(item_listbox)).pack(pady=5)

    def add_item(self, store_window):
        """Add a new item to the store."""
        name = simpledialog.askstring("Add Item", "Enter item name:")
        if name:
            price = simpledialog.askfloat("Add Item", "Enter item price:")
            if price is not None:
                new_item = {"name": name, "price": price}
                self.items.append(new_item)
                save_store_items(self.items)
                store_window.destroy()  # Close the manage window to refresh the items list
                self.manage_store()  # Refresh store management interface
                messagebox.showinfo("Success", f"Added new item: {name} - ${price:.2f}")
            else:
                messagebox.showerror("Error", "Invalid price.")
        else:
            messagebox.showerror("Error", "Item name cannot be empty.")

    def remove_item(self, item_listbox):
        """Remove an item from the store."""
        selected_item_index = item_listbox.curselection()
        if selected_item_index:
            item_to_remove = self.items[selected_item_index[0]]
            self.items.remove(item_to_remove)
            save_store_items(self.items)
            item_listbox.delete(selected_item_index)
            messagebox.showinfo("Success", f"Removed item: {item_to_remove['name']}")
        else:
            messagebox.showerror("Error", "Please select an item to remove.")

    def edit_item(self, item_listbox):
        """Edit an item in the store."""
        selected_item_index = item_listbox.curselection()
        if selected_item_index:
            item_to_edit = self.items[selected_item_index[0]]
            new_name = simpledialog.askstring("Edit Item", f"Enter new name for {item_to_edit['name']}:")
            if new_name:
                new_price = simpledialog.askfloat("Edit Item", f"Enter new price for {new_name}:")
                if new_price is not None:
                    item_to_edit['name'] = new_name
                    item_to_edit['price'] = new_price
                    save_store_items(self.items)
                    item_listbox.delete(selected_item_index)
                    item_listbox.insert(selected_item_index, f"{new_name} - ${new_price:.2f}")
                    messagebox.showinfo("Success", f"Edited item: {new_name} - ${new_price:.2f}")
                else:
                    messagebox.showerror("Error", "Invalid price.")
            else:
                messagebox.showerror("Error", "Item name cannot be empty.")
        else:
            messagebox.showerror("Error", "Please select an item to edit.")

# ----- RUN THE APPLICATION -----
if __name__ == "__main__":
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
