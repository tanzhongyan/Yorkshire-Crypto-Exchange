import Link from "next/link"
import { ArrowRight, Shield, BarChart3, Layers, Database, Server } from "lucide-react"
import { Button } from "@/components/ui/button"

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
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">Yorkshire Crypto Exchange</h1>
              <p className="text-xl text-muted-foreground max-w-2xl">
                Secure and efficient fiat-to-crypto transactions, wallet management, and trade execution built on a
                modern microservices architecture.
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
          <h2 className="text-3xl font-bold text-center mb-4">Built with Modern Technology</h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
            Yorkshire Crypto Exchange leverages cutting-edge technologies to deliver a robust and scalable platform.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 max-w-4xl mx-auto">
            <TechItem name="PostgreSQL" />
            <TechItem name="Next.js" />
            <TechItem name="Flask" />
            <TechItem name="RabbitMQ" />
            <TechItem name="Docker" />
            <TechItem name="TypeScript" />
            <TechItem name="SQLAlchemy" />
            <TechItem name="Kong API Gateway" />
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="py-16 bg-muted">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold mb-6">About Yorkshire Crypto Exchange</h2>
            <p className="text-lg text-foreground mb-6">
              Yorkshire Crypto Exchange is a microservices-based cryptocurrency exchange platform designed for secure
              and efficient fiat-to-crypto transactions, wallet management, and trade execution.
            </p>
            <p className="text-lg text-foreground mb-6">
              Built using Flask, Next.js, TypeScript, PostgreSQL, RabbitMQ, and Docker, it follows REST API
              best practices and utilizes message queues for asynchronous processing.
            </p>
            <p className="text-lg text-foreground">
              This project is part of the Enterprise Solution Design (ESD) course, demonstrating scalability,
              modularity, and real-world financial transaction handling in a containerized environment.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-card text-card-foreground py-12 mt-auto border-t">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-xl font-bold mb-4">Yorkshire Crypto Exchange</h3>
              <p className="text-muted-foreground">Secure, efficient, and modern cryptocurrency exchange platform.</p>
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
          <div className="border-t border-border mt-8 pt-8 text-center text-muted-foreground">
            <p>© {new Date().getFullYear()} Yorkshire Crypto Exchange. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="bg-card p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  )
}

function TechItem({ icon, name }) {
  return (
    <div className="flex items-center justify-center flex-col bg-card p-4 rounded-lg border shadow-sm">
      {icon && <div className="mb-2">{icon}</div>}
      <span className="font-medium">{name}</span>
    </div>
  )
}