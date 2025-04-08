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

After running `docker-compose`, access the API documentation:

- **Consolidated Swagger UI:**  
  [http://localhost:3001/swagger-ui](http://localhost:3001/swagger-ui)

- **Individual Microservice Endpoints:**

  **Atomic Microservices:**

  - **User Service:**  
    [http://localhost:5003/api/v1/user](http://localhost:5003/api/v1/user)

  - **Crypto Service:**  
    [http://localhost:5002/api/v1/crypto](http://localhost:5002/api/v1/crypto)

  - **Fiat Service:**  
    [http://localhost:5001/api/v1/fiat](http://localhost:5001/api/v1/fiat)

  - **Transaction Service:**  
    [http://localhost:5005/api/v1/transaction](http://localhost:5005/api/v1/transaction)

  - **Order Book Service (OutSystems):**  
    [https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1/](https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1/)

  **Composite Microservices:**

  - **Identity Service:**  
    [http://localhost:5004/api/v1](http://localhost:5004/api/v1)

  - **Deposit Service:**  
    [http://localhost:5006/api/v1](http://localhost:5006/api/v1)

  - **Ramp Service:**  
    [http://localhost:5007/api/v1](http://localhost:5007/api/v1)

  - **Market Service:**  
    [http://localhost:5008/api/v1](http://localhost:5008/api/v1)

  - **Initiate Service:**  
    [http://localhost:5009/api/v1/](http://localhost:5009/api/v1/)

  - **Complete Service:**  
    [http://localhost:5010/api/v1/](http://localhost:5010/api/v1/)

---

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