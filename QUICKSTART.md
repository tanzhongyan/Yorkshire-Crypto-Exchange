# 🚀 Quick Setup Guide

This guide provides streamlined steps to set up and test the Yorkshire Crypto Exchange project.

---

## ✅ Prerequisites

Ensure the following are installed:

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Node.js (v18 or later) with npm](https://nodejs.org/en)
- [Python (v3.9 or earlier)](https://www.python.org/downloads/)
- Optional: [Visual Studio Code](https://code.visualstudio.com/) with WSL enabled (for Windows)

---

## 🧪 Testing the Full Project Flow

1. **Clone the Repository**
   - Open with GitHub Desktop.

2. **Add the `setup-env.sh` File**

   - Obtain this script from `@tanzhongyan`.
   - Place it in the **root directory** of the project.

3. **Run the Setup Script**

   This script sets up necessary `.env` files.

   ```sh
   chmod +x setup-env.sh
   ./setup-env.sh
   ```

   > 💡 *For Windows users*, run this using Git Bash or WSL.

4. **Start Backend Services with Docker Compose**

   ```sh
   docker-compose up -d --build
   ```

   > 📦 This command initializes the database, API microservices, and Swagger UI documentation.

5. **Install Website Dependencies**

   Navigate to the website directory:

   ```sh
   cd website/yorkshire-crypto-exchange
   npm install
   ```

6. **Run the Website Frontend**

   ```sh
   npm run dev
   ```

   > 🌐 The website will be accessible at: [http://localhost:3000](http://localhost:3000)

---

## 🧾 Swagger API Documentation

Go to [Swagger UI](http://localhost:3001/swagger-ui) after running:  
```bash
docker-compose up -d --build
```

### 🔹 Atomic Microservices
- **[Fiat Service](http://localhost:5001/api/v1/fiat)**  
  Handles fiat currencies and user fiat accounts.
- **[Crypto Service](http://localhost:5002/api/v1/crypto)**  
  Manages crypto wallets and related operations.
- **[User Service](http://localhost:5003/api/v1/user)**  
  User account management – profiles, addresses, and authentication.
- **[Transaction Logs Service](http://localhost:5005/api/v1/transaction)**  
  Stores and retrieves transaction history logs.
- **[Orderbook Service](https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1/)**  
  Store current market orders (buy/sell listings).

### 🔸 Composite Microservices

- **[Manage Identity](http://localhost:5004/api/v1)**  
  Creates/deletes user-linked fiat and crypto accounts.
- **[Deposit Fiat](http://localhost:5006/api/v1)**  
  Allows fiat deposits via Stripe with webhook support.
- **[Ramp Crypto](http://localhost:5007/api/v1)**  
  Facilitates fiat ↔ crypto conversions (on/off ramp).
- **[Market Aggregator](http://localhost:5008/api/v1)**  
  Combines data from Coingecko, rates, orderbook, and executions for UI.
- **[Initiate Order](http://localhost:5009/api/v1/)**  
  Starts a new crypto order (buy/sell).
- **Match Order**  
  *No REST endpoint – uses AMQP only*  
  Matches new orders with existing ones in the orderbook.
- **[Complete Order](http://localhost:5010/api/v1/)**  
  Finalises and confirms crypto trades.

## ⚠️ Troubleshooting

- **Postgres Errors Due to Line Endings:**

   If you encounter errors related to the Postgres container, especially on Windows:

   1. **Convert Line Endings:**

      ```sh
      sudo apt install dos2unix
      dos2unix ./database/create-multiple-postgresql-databases.sh
      chmod +x ./database/create-multiple-postgresql-databases.sh
      ```

   2. **Restart Docker Services:**

      ```sh
      docker-compose down -v
      docker-compose up -d --build
      ```

- **Website Not Starting:**

   - Ensure `npm install` completed successfully.
   - If module errors persist:

     ```sh
     rm -rf node_modules
     npm install
     ```

---

## 📄 Additional Resources

- **Developer Setup, Migrations, and API Integration:**  
  Refer to [`DEVELOPMENT.md`](DEVELOPMENT.md)

- **Contribution Guidelines:**  
  See [`CONTRIBUTING.md`](CONTRIBUTING.md)