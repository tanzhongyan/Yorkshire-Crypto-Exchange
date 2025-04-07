# Deployment Guide

This guide provides step-by-step instructions on setting up and deploying this project.

## Setting Up Your Local Environment

Before running the project, ensure you have Python installed and install dependencies:

1. **Verify Python Installation**

   ```sh
   python --version
   ```

   Ensure Python version **3.9 or earlier** is installed.

   Do this inside VSCode terminal. If the output is an error, check the following:
   - In search bar, search "add or remove programs". Search "python" within "add or remove programs". It should show the version of python you have installed.
   - If there's nothing there, install it at [python.org](https://www.python.org/downloads/). The latest stable version is version 3.13.
   - After installing it, in VSCode,
      - press `ctrl` + `shift` + `p`
      - search "python: create environment"
      - Click on "Venv"
      - Click on the latest version of python you have
      - Tick "requirements.txt" checkbox and press "OK"
      - Your repository should now have a ".venv" file.

2. **Install Required Dependencies**
   Navigate to the project's root directory and install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

## Before Running Docker Compose

If you're facing issues with missing environment variables such as:
- **STRIPE API KEYs**
- **EXCHANGE RATE API KEY**
- **GMAIL USER and PASSWORD**

This is because `.env` files are not stored in Git. Run the setup script from `@tanzhongyan` (either bash or PowerShell) **before** running `docker-compose` for the first time.

## Running Docker Compose

To initialise and start the database and microservices, run:

```sh
docker-compose up -d --build
```

- `-d` runs the services in the background.
- `--build` rebuilds images before starting containers.

### How It Works

1. **Docker Compose builds the database container first**:
   - Traditionally, `depends_on` runs services immediately after the container is up.
   - A **healthcheck** is added to ensure the database is fully set up before other services start.

**KNOWN ERROR:** If you face issues when deploying the postgres container like "user_db" not found, it is likely caused by an incompatibility issue between windows and linux line endings.

- Run:

   ```sh
   docker-compose down -v
   ```

**Windows user**
- In your VSCode local terminal, run:
   ```
   sudo apt update && sudo apt install dos2unix -y
   ```

   ```sh
   wsl dos2unix ./database/create-multiple-postgresql-databases.sh
   ```

   ```
   file ./database/create-multiple-postgresql-databases.sh
   ```

   If it says "ASCII text" or "Bourne-Again shell script", it's now Unix-compatible.

**mac user**
- In your VSCode local terminal, run:
   ```
   brew install dos2unix
   ```

   ```
   dos2unix ./database/create-multiple-postgresql-databases.sh
   ```

   ```
   file ./database/create-multiple-postgresql-databases.sh
   ```
   If it says "ASCII text" or "Bourne-Again shell script", it's now Unix-compatible.

- Run:
   ```
   chmod +x ./database/create-multiple-postgresql-databases.sh
   ```

- Run:

   ```sh
   docker-compose up -d --build
   ```

2. **Microservices start after the database is ready**:
   - Navigate into the respective microservice directory before running migrations:

     ```sh
     cd ./api/atomic/user  # or ./api/atomic/fiat, ./api/atomic/crypto
     ```

   - The migration file is executed to initialise database tables.
   - `app.py` starts after migrations complete.

3. **Seeding Data (First-Time Setup)**:
   - If this is the first time running, `app.py` will populate the database using `seeddata.json`.

## Flask Migrate

[Flask-Migrate](https://flask-migrate.readthedocs.io/) is used as an ORM for database management.

### Benefits

- Reduces the need for raw SQL queries.
- Simplifies schema management for future cloud deployment.

### First-Time Database Migration

Navigate to the microservice folder first:

```sh
cd ./api/atomic/user  # or ./api/atomic/fiat, ./api/atomic/crypto
```

Run the following commands to create the migration files and apply them:

```sh
flask db init
flask db migrate -m "Initial migration."
flask db upgrade
```

Migration files should appear inside the `migrations/` folder.

### Example Table Definition

```python
class UserAccount(db.Model):
    __tablename__ = 'user_account'
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(50), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

    # Relationships
    authentication = db.relationship('UserAuthenticate', back_populates='user', uselist=False, cascade='all, delete-orphan')
    addresses = db.relationship('UserAddress', back_populates='user', cascade='all, delete-orphan')
```

## Flask-RESTx

[Flask-RESTx](https://flask-restx.readthedocs.io/) is used to automatically generate API documentation.

### Example of Flask-RESTx Initialisation

To define your API root, ensure to declare the variable within your code:
```
API_VERSION = 'v1'
API_ROOT = f'/{API_VERSION}/api/user'
```

To start all route prefixes with your `API_ROOT`, you will have to create Blueprint and add it to your Api object:
```
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='User API', description='User API for Yorkshire Crypto Exchange')
```

Thereafter, you'll need to add register the Blueprint with Flask app:
```
app.register_blueprint(blueprint)
```

### Example of Flask-RESTx Namespace Setup

Namespaces are used to group related CRUD operations for atomic microservices.

The example below shows a namespace created just for the account table that the user entity owns:
```
account_ns = Namespace('account', description='Account related operations')
```

### Example of Flask-RESTx Model Setup

Models are used to define the input and output variables required":

```
user_input_model = account_ns.model(
    "UserInput",
    {
        "username": fields.String(required=True, description="The username"),
        "fullname": fields.String(required=True, description="The full name"),
        "phone": fields.String(required=True, description="The phone number"),
        "email": fields.String(required=True, description="The email address"),
    },
)
```

```python
user_output_model = account_ns.model(
    "UserOutput",
    {
        "userId": fields.String(attribute="user_id", readOnly=True, description="The unique identifier of a user"),
        "username": fields.String(required=True, description="The username"),
        "fullname": fields.String(required=True, description="The full name"),
        "phone": fields.String(required=True, description="The phone number"),
        "email": fields.String(required=True, description="The email address"),
    },
)
```

### CRUD Example

- Use your created Namespace variable as the flask app and pass in the routes. The API naming convention will follow the `API_ROOT` followed by `/{namespace}` and `/{specified-route}`. An example would be:
  - `API_ROOT`: "/api/v1/user"
  - `namespace`: "account"
  - `specified-route`: ""
```
localhost:5003/api/v1/user/account
```
- Use `expect` to specify the input parameters. Pass in the **input model** as the parameter.
- Use `marshal_list_with` when you want to get all records. Pass in the **output model** as the parameter.
- Use `marshal_with` when you want to get one record. Pass in the **output model** as the parameter.

```python
@account_ns.route("")
class UserAccountListResource(Resource):
    @account_ns.marshal_list_with(user_output_model)
    def get(self):
        """Fetch all user accounts"""
        return UserAccount.query.all()

    @account_ns.expect(user_input_model, validate=True)
    @account_ns.marshal_with(user_output_model, code=201)
    def post(self):
        """Create a new user account"""
        data = request.json
        new_user = UserAccount(
            username=data.get('username'),
            fullname=data.get('fullname'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user, 201
```

### Accessing API Documentation

Each microservice hosts its documentation at:

Atomic Microservices:
- **Fiat Service:** `http://localhost:5001/api/v1/fiat`
- **Crypto Service:** `http://localhost:5002/api/v1/crypto`
- **User Service:** `http://localhost:5003/api/v1/user`
- **transaction Service:** `http://localhost:5005/api/v1/transaction`

Composite Microservices:
- **identity** `http://localhost:5004/api/v1`
- **deposit** `http://localhost:5006/api/v1`
- **ramp** `http://localhost:5007/api/v1`
- **market** `http://localhost:5008/api/v1`
- **order-initiation** `http://localhost:5009/api/v1/`

### Kong Gateway Configuration

Ensure that your `kong.yml` includes both service definitions and JWT plugin setup as follows:

Example
```
   - name: fiat-service
      url: http://fiat-service:5000
      routes:
      - name: fiat-route
         paths:
            - /api/v1/fiat
         strip_path: false
         plugins:
            - name: jwt
```

## Running the Website Locally
This documentation provides instructions for setting up and running the **Yorkshire Crypto Exchange Website** stored under `/website/yorkshire-crypto-exchange`.

### Step 1: Install Dependencies

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

### Step 2: Run the Development Server

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

### Module Not Found Error

Ensure dependencies are installed:

```sh
npm install
```

## Integration APIs to frontend
For every page, make sure that you have the following import at the top.
```
import axios from "@/lib/axios";
```

This is an example of how to use it. If you use axios here, it will pre-append JWT token to allow for authentication.
Example
```
   const response = await axios.post("/api/v1/ramp/swap", {
      user_id: userId,
      amount: parseFloat(fromAmount),
      fiat_currency: direction === "fiattocrypto" ? fromCurrency : toCurrency,
      token_id: direction === "fiattocrypto" ? toCurrency : fromCurrency,
      direction: direction
   });
```

## Accessing Database Data (Visualisation)

You can visualise database data using **DBeaver**:

1. **Download and install [DBeaver](https://dbeaver.io/)**.
2. **Create a PostgreSQL connection** with the following credentials:
   - **Host:** `localhost`
   - **Port:** `5433`
   - **Username:** `user`
   - **Password:** `password`
3. Click **OK**, then connect. You can now browse and query your database.

This guide ensures a smooth setup and deployment process. Happy coding!
