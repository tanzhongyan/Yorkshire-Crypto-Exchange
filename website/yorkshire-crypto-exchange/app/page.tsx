import Link from "next/link";
import { ArrowRight, Shield, BarChart3, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import DashboardFooter from "@/components/footer";

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Sticky Navigation */}
      <nav className="sticky top-0 z-50 bg-background border-b">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-foreground font-bold text-xl">
                Yorkshire Crypto
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Button asChild variant="outline">
                <Link href="/login">Sign In</Link>
              </Button>
              <Button asChild>
                <Link href="/signup">Create Account</Link>
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="bg-card text-card-foreground">
        <div className="container mx-auto px-4 py-16 md:py-24">
          <div className="flex flex-col md:flex-row items-center justify-between gap-12">
            <div className="md:w-1/2 space-y-6">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">
                Yorkshire Crypto Exchange
              </h1>
              <p className="text-xl text-muted-foreground max-w-2xl">
                Secure and efficient fiat-to-crypto transactions, wallet
                management, and trade execution built on a modern microservices
                architecture.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 pt-4">
                <Button asChild size="lg">
                  <Link href="/signup">
                    Create Account <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
            <div className="md:w-1/2 flex justify-center">
              <div className="relative w-full max-w-md">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-accent rounded-lg blur opacity-30"></div>
                <div className="relative bg-card p-6 rounded-lg border">
                  <img
                    src="/heroimg.png"
                    alt="Yorkshire Crypto Exchange Platform"
                    className="w-full rounded-md"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Features Section */}
      <section className="py-16 bg-muted">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">Key Features</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Shield className="h-10 w-10 text-primary" />}
              title="Secure Transactions"
              description="Enterprise-grade security for all fiat and cryptocurrency transactions with multi-layer protection."
            />
            <FeatureCard
              icon={<Layers className="h-10 w-10 text-primary" />}
              title="Microservices Architecture"
              description="Modular, scalable design ensuring high availability and resilience for all exchange operations."
            />
            <FeatureCard
              icon={<BarChart3 className="h-10 w-10 text-primary" />}
              title="Advanced Trading"
              description="Powerful trading tools and real-time market data for both beginners and experienced traders."
            />
          </div>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="py-16 bg-background">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">
            Built with Modern Technology
          </h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
            Yorkshire Crypto Exchange leverages cutting-edge technologies to
            deliver a robust and scalable platform.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 max-w-4xl mx-auto">
            <TechItem name="PostgreSQL" icon={undefined} />
            <TechItem name="Next.js" icon={undefined} />
            <TechItem name="Flask" icon={undefined} />
            <TechItem name="RabbitMQ" icon={undefined} />
            <TechItem name="Docker" icon={undefined} />
            <TechItem name="TypeScript" icon={undefined} />
            <TechItem name="SQLAlchemy" icon={undefined} />
            <TechItem name="Kong API Gateway" icon={undefined} />
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="py-16 bg-muted">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold mb-6">
              About Yorkshire Crypto Exchange
            </h2>
            <p className="text-lg text-foreground mb-6">
              Yorkshire Crypto Exchange is a microservices-based cryptocurrency
              exchange platform designed for secure and efficient fiat-to-crypto
              transactions, wallet management, and trade execution.
            </p>
            <p className="text-lg text-foreground mb-6">
              Built using Flask, Next.js, TypeScript, PostgreSQL, RabbitMQ, and
              Docker, it follows REST API best practices and utilizes message
              queues for asynchronous processing.
            </p>
            <p className="text-lg text-foreground">
              This project is part of the Enterprise Solution Design (ESD)
              course, demonstrating scalability, modularity, and real-world
              financial transaction handling in a containerized environment.
            </p>
          </div>
        </div>
      </section>

      {/* Team Members Section */}
      <section className="py-16 bg-background">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">
            Team Members & Contributions
          </h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
            Meet the developers behind Yorkshire Crypto Exchange and their contributions to the project.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Primary Contributors */}
            <TeamMemberCard
              name="Tan Zhong Yan"
              githubUrl="https://github.com/tanzhongyan"
              role="Technical Lead / Full-Stack Developer"
              scope="Full system architecture, service development, and integration"
              contributions={[
                "Set up and configured the core development infrastructure, including GitHub repository, Docker Compose, Kong API Gateway, JWT authentication, and Stripe integration.",
                "Led the backend stack configuration and automation using Flask-RestX, Flask-Migrate, and GitHub Actions.",
                "Designed and implemented core atomic services: user, fiat, crypto, and transaction.",
                "Developed major composite services: identity, deposit, ramp, and complete.",
                "Integrated all backend microservices into the frontend application.",
                "Consolidated and deployed a unified API testing interface for all services."
              ]}
              isPrimary={true}
            />
            
            <TeamMemberCard
              name="Wu Chensang"
              githubUrl="https://github.com/Chensang-Wu"
              role="Backend Developer / Frontend Integrator"
              scope="Market data aggregation and UI integration"
              contributions={[
                "Developed the market composite service that aggregates data from CoinGecko and formats it based on defined business logic.",
                "Integrated the market service into the frontend buy dashboard.",
                "Produced and edited the final demo video showcasing project functionalities.",
                "Conducted technical explorations on GraphQL and Twilio (not included in final deployment)."
              ]}
              isPrimary={true}
            />
            
            <TeamMemberCard
              name="Shahul Hameed"
              githubUrl="https://github.com/ShahulHameedBZR"
              role="Systems Analyst / Trading Logic Architect"
              scope="Execution engine, algorithmic logic, and microservice coordination"
              contributions={[
                "Designed and implemented the orderbook atomic service, including custom logic for market and limit orders.",
                "Created the match-order service with full matching algorithms: exact, cascading, partial fulfilment, and rollback handling.",
                "Developed robust error handling logic and internal notification triggers based on execution outcomes.",
                "Led standardisation efforts on trading logic and internal process documentation."
              ]}
              isPrimary={true}
            />
            
            {/* Supporting Contributors */}
            <TeamMemberCard
              name="Jamesz Lau"
              githubUrl="https://github.com/JameszLau"
              role="Service Developer"
              scope="Select microservices and message queue setup"
              contributions={[
                "Built the crypto atomic service and initiate-order composite service.",
                "Set up RabbitMQ for inter-service messaging using Docker and custom scripts.",
                "Contributed to system diagrams and architectural breakdowns."
              ]}
              isPrimary={true}
            />
            
            <TeamMemberCard
              name="Jacob Roy"
              githubUrl="https://github.com/jacobr7"
              role="Support Developer"
              scope="Event-driven processing and backend service support"
              contributions={[
                "Assisted in the development of the order-completion composite service, which listens to message queues and triggers transaction updates.",
                "Supported initial work on atomic services and system design discussions."
              ]}
              isPrimary={false}
            />
            
            <TeamMemberCard
              name="Christin Choo"
              githubUrl="https://github.com/choowieeee"
              role="Contributor"
              scope="Minor service-level contributions"
              contributions={[
                "Provided development support on several atomic (user, fiat, transaction) and composite services (deposit, ramp)."
              ]}
              isPrimary={false}
            />
          </div>
          
          <div className="text-center mt-12">
            <a 
              href="https://github.com/tanzhongyan/Yorkshire-Crypto-Exchange/graphs/contributors" 
              target="_blank" 
              rel="noopener noreferrer"
              className="inline-flex items-center text-primary hover:underline"
            >
              View all contributions on GitHub
              <ArrowRight className="ml-2 h-4 w-4" />
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-card text-card-foreground py-12 mt-auto border-t">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-xl font-bold mb-4">
                Yorkshire Crypto Exchange
              </h3>
              <p className="text-muted-foreground">
                Secure, efficient, and modern cryptocurrency exchange platform.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-bold mb-4">Documentation</h3>
              <ul className="space-y-2 text-muted-foreground">
                <li>
                  <a
                    href="https://github.com/tanzhongyan/Yorkshire-Crypto-Exchange/blob/main/DEVELOPMENT.md"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-primary"
                  >
                    Development Guide
                  </a>
                </li>
                <li>
                  <a
                    href="https://github.com/tanzhongyan/Yorkshire-Crypto-Exchange/blob/main/CONTRIBUTING.md"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-primary"
                  >
                    Contributing
                  </a>
                </li>
                <li>
                  <a
                    href="https://github.com/tanzhongyan/Yorkshire-Crypto-Exchange"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-primary"
                  >
                    GitHub Repository
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-xl font-bold mb-4">Get Started</h3>
              <ul className="space-y-2 text-muted-foreground">
                <li>
                  <Link href="/signup" className="hover:text-primary">
                    Create Account
                  </Link>
                </li>
                <li>
                  <Link href="/login" className="hover:text-primary">
                    Sign In
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className= "mt-8 pt-8 text-center text-muted-foreground">
            <DashboardFooter />
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="bg-card p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}

function TechItem({ icon, name }) {
  return (
    <div className="flex items-center justify-center flex-col bg-card p-4 rounded-lg border shadow-sm">
      {icon && <div className="mb-2">{icon}</div>}
      <span className="font-medium">{name}</span>
    </div>
  );
}

function TeamMemberCard({ name, githubUrl, role, scope, contributions, isPrimary }) {
  return (
    <div className={`bg-card p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow ${isPrimary ? 'border-primary/30' : ''}`}>
      <h3 className="text-xl font-bold mb-1">
        <a 
          href={githubUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="hover:text-primary hover:underline flex items-center"
        >
          {name}
          <svg className="h-4 w-4 ml-2" viewBox="0 0 16 16" fill="currentColor">
            <path fillRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
          </svg>
        </a>
      </h3>
      <div className={`inline-block px-3 py-1 rounded-full text-sm mb-3 ${isPrimary ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
        {role}
      </div>
      <p className="text-muted-foreground mb-3 text-sm">
        <strong>Scope:</strong> {scope}
      </p>
      <h4 className="font-semibold mb-2">Contributions:</h4>
      <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
        {contributions.map((contribution, index) => (
          <li key={index}>{contribution}</li>
        ))}
      </ul>
    </div>
  );
}