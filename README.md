# 🎓 EduMart – Education E-Commerce Platform

EduMart is a colorful and user-friendly education e-commerce platform where students can discover and purchase educational resources from different vendors.

The platform includes separate authentication and dashboards for **Users, Vendors, and Administrators**.

## ✨ Features

### 👨‍🎓 User
- User registration and login
- Browse approved educational products
- Search and explore products
- View product details
- Add products to cart
- Checkout
- View order history

### 👨‍🏫 Vendor
- Vendor registration and login
- Add educational products
- Upload product details and images
- Track product approval status
- Manage uploaded products

### 👨‍💼 Admin
- Secure admin login
- View vendor-submitted products
- Approve products
- Reject products
- Manage the educational marketplace

## 🔄 Product Approval Workflow

```text
Vendor uploads product
        ↓
Product status = Pending
        ↓
Admin reviews product
        ↓
   ┌────┴────┐
   ↓         ↓
Approve    Reject
   ↓
Product becomes
visible to users
