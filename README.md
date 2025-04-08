# Yorkshire Crypto Exchange 🚀

Yorkshire Crypto Exchange is a microservices-based cryptocurrency exchange platform designed for secure and efficient fiat-to-crypto transactions, wallet management, and trade execution. Built using Flask, Next.js, Node.js, Typescript, PostgreSQL, RabbitMQ, and Docker, it follows REST API best practices and utilizes message queues for asynchronous processing. This project is part of the Enterprise Solution Design (ESD) course, demonstrating scalability, modularity, and real-world financial transaction handling in a containerized environment.

## 🛠 Tech Stack

- **Database:** PostgreSQL
- **Website:** Next.js, Typescript (Vercel V0)
- **API:** Flask + Pika (RabbitMQ) + Kong API gateway
- **ORM:** Flask-Migrate + SQLAlchemy
- **CI/CD:** GitHub Actions
- **Python Formatting:** Black (PEP8 style guide)
- **Auto-generate Changelog:** Release Changelog Builder
- **Authentication** JSON Web Tokens (JWT)
- **API Documentation:** Flask-RESTx
- **Coding Standards:** Pylint
- **Containerization:** Docker-Compose (Database, APIs, Website, RabbitMQ)

## 📜 Documentation
- **[QUICKSTART.md](QUICKSTART.md)** - For newcomers to quickly set up
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development setup and coding standards
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines, branching strategy, and PR guide

## 📥 Installation & Setup

It is recommended to use [QUICKSTART.md](QUICKSTART.md) for new users.

### Set up docker containers
1. Get `setup-env.sh` from @tanzhongyan to get .env files required to run the project.

2. Start the services using Docker Compose:
   ```sh
   docker-compose up -d --build
   ```

## 📚 Consolidated API Documentation
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
- **[Manage Identity Service](http://localhost:5004/api/v1)**  
  Creates/deletes user-linked fiat and crypto accounts.
- **[Deposit Fiat Service](http://localhost:5006/api/v1)**  
  Allows fiat deposits via Stripe with webhook support.
- **[Ramp Crypto Service](http://localhost:5007/api/v1)**  
  Facilitates fiat ↔ crypto conversions (on/off ramp).
- **[Market Aggregator Service](http://localhost:5008/api/v1)**  
  Combines data from Coingecko, rates, orderbook, and executions for UI.
- **[Initiate Order Service](http://localhost:5009/api/v1/)**  
  Starts a new crypto order (buy/sell).
- **Match Order Service**  
  *No REST endpoint – uses AMQP only*  
  Matches new orders with existing ones in the orderbook.
- **[Complete Order Service](http://localhost:5010/api/v1/)**  
  Finalises and confirms crypto trades.

## 💻 Set up front end website
1. Install Dependencies

Before running the website, navigate to the project directory and install the necessary dependencies:

```sh
cd website/yorkshire-crypto-exchange
npm install
```

Alternatively, if using Yarn:

```sh
cd website/yorkshire-crypto-exchange
yarn install
```

2. Run the Development Server

To start the Next.js development server, run:

```sh
npm run dev
```

Or, if using Yarn:

```sh
yarn dev
```

Once the server starts, the website will be available at:

```
http://localhost:3000
```

## 📌 Features
- **Secure transactions** between fiat and crypto
- **Microservices architecture** with modular scalability
- **Message queue processing** using RabbitMQ
- **Automated API documentation** with Flask-RESTx
- **Containerized deployment** with Docker

## 🤝 Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting changes, PRs, and reviewing contributions.

## 📝 License
This project is licensed under the [MIT License](LICENSE).