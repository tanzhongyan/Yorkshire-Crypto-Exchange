from flask import Flask, render_template, jsonify, request, render_template_string, redirect
import requests

app = Flask(__name__)

# Define your microservices with their URLs and descriptions
atomic_services = {
    "Fiat Service": {
        "url": "http://localhost:5001/api/v1/fiat",
        "description": "Manages fiat currency operations",
        "platform": "Docker"
    },
    "Crypto Service": {
        "url": "http://localhost:5002/api/v1/crypto",
        "description": "Handles crypto currency operations",
        "platform": "Docker"
    },
    "User Service": {
        "url": "http://localhost:5003/api/v1/user",
        "description": "User account management",
        "platform": "Docker"
    },
    "Transaction Service": {
        "url": "http://localhost:5005/api/v1/transaction",
        "description": "Transaction records for fiat, fiattocrypto, crypto, and aggregated transactions",
        "platform": "Docker"
    },
    "OrderBook Service": {
        "url": "https://personal-qrtp80l4.outsystemscloud.com/OrderBook_API/rest/v1",
        "description": "OrderBook API",
        "platform": "OutSystems"
    }
}

composite_services = {
    "Identity": {
        "url": "http://localhost:5004/api/v1",
        "description": "Identity, wallet and account creation/deletion"
    },
    "Deposit": {
        "url": "http://localhost:5006/api/v1",
        "description": "Manages fiat deposit operations"
    },
    "Ramp": {
        "url": "http://localhost:5007/api/v1",
        "description": "Fiat to crypto ramp services"
    },
    "Market": {
        "url": "http://localhost:5008/api/v1",
        "description": "Coingecko, exchangerate, orderbook, and executions data"
    },
    "Initiate": {
        "url": "http://localhost:5009/api/v1",
        "description": "Initiates crypto order processes"
    },
    "Complete": {
        "url": "http://localhost:5010/api/v1",
        "description": "Completes and finalizes crypto order transactions"
    }
}

@app.route('/')
def index():
    # Redirect straight to the merged documentation
    return redirect('/swagger-ui')

@app.route('/swagger-ui')
def swagger_ui():
    swagger_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Microservices API Documentation</title>
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <!-- Bootstrap Icons -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <!-- Swagger UI CSS -->
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css">
        <style>
            body {
                margin: 0;
                padding: 0;
                height: 100vh;
                overflow: hidden;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            #main-container {
                display: flex;
                height: 100vh;
            }
            #sidebar {
                width: 280px;
                height: 100%;
                overflow-y: auto;
                background-color: #212529;
                color: #fff;
                transition: all 0.3s;
            }
            #sidebar.collapsed {
                margin-left: -280px;
            }
            #content {
                flex: 1;
                height: 100vh;
                overflow-y: auto;
                transition: all 0.3s;
                display: flex;
                flex-direction: column;
            }
            .sidebar-header {
                padding: 20px;
                background-color: #0d6efd;
                color: white;
            }
            .sidebar-menu {
                padding: 15px;
            }
            .service-category {
                margin-top: 20px;
                margin-bottom: 10px;
                color: #0d6efd;
                font-weight: 500;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 1px;
                border-bottom: 1px solid #444;
                padding-bottom: 5px;
            }
            .platform-category {
                margin-top: 10px;
                margin-bottom: 5px;
                font-weight: 500;
                font-size: 0.85em;
                padding-left: 10px;
            }
            .nav-link {
                color: #ced4da;
                transition: all 0.2s;
                padding: 8px 10px;
                margin: 2px 0;
                border-radius: 5px;
                display: flex;
                align-items: center;
            }
            .nav-link:hover, .nav-link.active {
                background-color: #0d6efd;
                color: white;
                text-decoration: none;
            }
            .nav-link i {
                margin-right: 10px;
            }
            .navbar {
                padding: 10px 20px;
                background-color: #fff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            #swagger-content {
                flex: 1;
                padding: 0;
                background-color: #f8f9fa;
            }
            #swagger-ui {
                max-width: 100%;
                height: 100%;
            }
            .navbar-brand {
                font-weight: bold;
                color: #0d6efd;
            }
            .swagger-ui .topbar {
                display: none;
            }
            .toggle-btn {
                margin-right: 15px;
                cursor: pointer;
                color: #0d6efd;
                font-size: 1.5rem;
            }
            #service-selector {
                min-width: 250px;
            }
            .service-description {
                font-size: 0.8em;
                opacity: 0.8;
                display: block;
                margin-top: 3px;
            }
        </style>
    </head>
    <body>
        <div id="main-container">
            <!-- Sidebar -->
            <div id="sidebar">
                <div class="sidebar-header">
                    <h5 class="mb-0">API Documentation</h5>
                </div>
                <div class="sidebar-menu">
                    <div>
                        <div class="service-category">Atomic Microservices</div>
                        <div class="platform-category">OutSystems</div>
                        <nav class="nav flex-column ps-2">
                            {% for name, details in atomic_services.items() %}
                                {% if details.platform == "OutSystems" %}
                                <a class="nav-link service-link" data-url="{{ details.url }}/swagger.json">
                                    <div>
                                        <i class="bi bi-box"></i> {{ name }}
                                        <span class="service-description">{{ details.description }}</span>
                                    </div>
                                </a>
                                {% endif %}
                            {% endfor %}
                        </nav>
                        
                        <div class="platform-category">Docker</div>
                        <nav class="nav flex-column ps-2">
                            {% for name, details in atomic_services.items() %}
                                {% if details.platform == "Docker" %}
                                <a class="nav-link service-link" data-url="{{ details.url }}/swagger.json">
                                    <div>
                                        <i class="bi bi-box"></i> {{ name }}
                                        <span class="service-description">{{ details.description }}</span>
                                    </div>
                                </a>
                                {% endif %}
                            {% endfor %}
                        </nav>
                    </div>
                    <div>
                        <div class="service-category">Composite Microservices</div>
                        <nav class="nav flex-column">
                            {% for name, details in composite_services.items() %}
                            <a class="nav-link service-link" data-url="{{ details.url }}/swagger.json">
                                <div>
                                    <i class="bi bi-boxes"></i> {{ name }}
                                    <span class="service-description">{{ details.description }}</span>
                                </div>
                            </a>
                            {% endfor %}
                        </nav>
                    </div>
                </div>
            </div>
            
            <!-- Content -->
            <div id="content">
                <nav class="navbar">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-list toggle-btn" id="toggle-sidebar"></i>
                        <span class="navbar-brand mb-0 h1">Microservices API Explorer</span>
                    </div>
                    <div>
                        <select id="service-selector" class="form-select">
                            <optgroup label="Atomic Microservices - OutSystems">
                                {% for name, details in atomic_services.items() %}
                                    {% if details.platform == "OutSystems" %}
                                    <option value="{{ details.url }}/swagger.json">{{ name }}</option>
                                    {% endif %}
                                {% endfor %}
                            </optgroup>
                            <optgroup label="Atomic Microservices - Docker">
                                {% for name, details in atomic_services.items() %}
                                    {% if details.platform == "Docker" %}
                                    <option value="{{ details.url }}/swagger.json">{{ name }}</option>
                                    {% endif %}
                                {% endfor %}
                            </optgroup>
                            <optgroup label="Composite Microservices">
                                {% for name, details in composite_services.items() %}
                                <option value="{{ details.url }}/swagger.json">{{ name }}</option>
                                {% endfor %}
                            </optgroup>
                        </select>
                    </div>
                </nav>
                <div id="swagger-content">
                    <div id="swagger-ui"></div>
                </div>
            </div>
        </div>
        
        <!-- Bootstrap JS -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <!-- Swagger UI Bundle -->
        <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js"></script>
        
        <script>
            // Toggle sidebar
            document.getElementById('toggle-sidebar').addEventListener('click', function() {
                document.getElementById('sidebar').classList.toggle('collapsed');
            });
            
            // Handle loading Swagger UI
            window.onload = function() {
                // Initialize with the first service
                const select = document.getElementById('service-selector');
                initSwaggerUI(select.value);
                
                // Mark the first service as active
                const firstLink = document.querySelector('.service-link');
                if (firstLink) {
                    firstLink.classList.add('active');
                }
                
                // Add change listener to dropdown
                select.addEventListener('change', function() {
                    const url = this.value;
                    initSwaggerUI(url);
                    updateActiveLink(url);
                });
                
                // Add click listeners to sidebar links
                const serviceLinks = document.querySelectorAll('.service-link');
                serviceLinks.forEach(link => {
                    link.addEventListener('click', function() {
                        const url = this.getAttribute('data-url');
                        select.value = url; // Update dropdown selection
                        initSwaggerUI(url);
                        updateActiveLink(url);
                    });
                });
            };
            
            // Initialize Swagger UI
            function initSwaggerUI(url) {
                const ui = SwaggerUIBundle({
                    url: url,
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    docExpansion: "list",
                    syntaxHighlight: {
                        activate: true,
                        theme: "agate"
                    },
                    filter: true,
                    requestInterceptor: (request) => {
                        return request;
                    }
                });
                window.ui = ui;
            }
            
            // Update active class on sidebar links
            function updateActiveLink(url) {
                const links = document.querySelectorAll('.service-link');
                links.forEach(link => {
                    if (link.getAttribute('data-url') === url) {
                        link.classList.add('active');
                    } else {
                        link.classList.remove('active');
                    }
                });
            }
        </script>
    </body>
    </html>
    """
    
    # Convert service data structure for template
    return render_template_string(swagger_template, 
                                 atomic_services=atomic_services,
                                 composite_services=composite_services)

@app.route('/combined-swagger.json')
def combined_swagger():
    # Base template for the combined swagger
    combined = {
        "openapi": "3.0.0",
        "info": {
            "title": "Combined Microservices API",
            "description": "Documentation for all microservices",
            "version": "1.0.0"
        },
        "paths": {},
        "components": {
            "schemas": {}
        }
    }
    
    # Fetch and merge all services
    all_services = {}
    for name, details in atomic_services.items():
        all_services[name] = details["url"]
    for name, details in composite_services.items():
        all_services[name] = details["url"]
    
    for name, url in all_services.items():
        try:
            response = requests.get(f"{url}/swagger.json")
            if response.status_code == 200:
                service_spec = response.json()
                
                # Add service paths with service name prefix to avoid conflicts
                if "paths" in service_spec:
                    for path, methods in service_spec["paths"].items():
                        # Add service name to path to avoid conflicts
                        new_path = f"/{name.lower().replace(' ', '-')}{path}"
                        combined["paths"][new_path] = methods
                
                # Merge components/schemas
                if "components" in service_spec and "schemas" in service_spec["components"]:
                    for schema_name, schema in service_spec["components"]["schemas"].items():
                        # Add service prefix to schema names to avoid conflicts
                        new_schema_name = f"{name.lower().replace(' ', '_')}_{schema_name}"
                        combined["components"]["schemas"][new_schema_name] = schema
                        
        except Exception as e:
            print(f"Error fetching {name} swagger: {str(e)}")
    
    return jsonify(combined)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)