"use client"

import { useState, useEffect } from "react"
import { ArrowUpRight, Wallet, ChevronLeft, ChevronRight } from "lucide-react"
import { getCookie } from "@/lib/cookies"
import axios from "@/lib/axios"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AreaChart, BarChart } from "@/components/chart"
import { Button } from "@/components/ui/button"

// Mock data for the charts
const areaChartData = [
  { name: "Jan", value: 2000 },
  { name: "Feb", value: 4000 },
  { name: "Mar", value: 3000 },
  { name: "Apr", value: 5000 },
  { name: "May", value: 4000 },
  { name: "Jun", value: 6000 },
  { name: "Jul", value: 5500 },
  { name: "Aug", value: 7000 },
  { name: "Sep", value: 8000 },
  { name: "Oct", value: 7500 },
  { name: "Nov", value: 9000 },
  { name: "Dec", value: 10000 },
]

const barChartData = [
  { name: "BTC", value: 4000 },
  { name: "ETH", value: 3000 },
  { name: "USDT", value: 2000 },
  { name: "BNB", value: 1500 },
  { name: "SOL", value: 1000 },
]

// Mock wallet data
const wallets = [
  { id: 1, name: "Bitcoin", symbol: "BTC", balance: 0.05, value: 3245.67, change: 2.5 },
  { id: 2, name: "Ethereum", symbol: "ETH", balance: 1.2, value: 2876.43, change: -1.2 },
  { id: 3, name: "Tether", symbol: "USDT", balance: 1000, value: 1000, change: 0 },
  { id: 4, name: "Singapore Dollar", symbol: "SGD", balance: 5000, value: 5000, change: 0 },
]

export default function DashboardPage() {
  const [mounted, setMounted] = useState(false)
  const [transactions, setTransactions] = useState([])
  const [pagination, setPagination] = useState({
    total: 0,
    pages: 0,
    page: 1,
    per_page: 10
  })
  const [loading, setLoading] = useState(false)
  const userId = getCookie("userId")

  useEffect(() => {
    setMounted(true)
  }, [])

  const fetchTransactions = async (page = 1) => {
    if (!userId) return
    
    setLoading(true)
    try {
      const response = await axios.get(`/api/v1/transaction/aggregated/user/${userId}`, {
        params: {
          page,
          per_page: 10
        }
      })
      
      setTransactions(response.data.transactions)
      setPagination(response.data.pagination)
    } catch (error) {
      console.error("Failed to load transactions:", error)
    } finally {
      setLoading(false)
    }
  }

  const handlePageChange = (newPage) => {
    fetchTransactions(newPage)
  }

  // Initial load of transactions
  useEffect(() => {
    if (mounted && userId) {
      fetchTransactions(1)
    }
  }, [mounted, userId])

  // Format dates for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Format transaction amount for display
  const formatTransactionDisplay = (transaction) => {
    switch (transaction.transactionType) {
      case 'fiat':
        return {
          title: transaction.type === 'deposit' 
            ? `Deposited ${transaction.currencyCode.toUpperCase()}` 
            : `Withdrew ${transaction.currencyCode.toUpperCase()}`,
          amount: `${transaction.type === 'deposit' ? '+' : '-'}${transaction.amount} ${transaction.currencyCode.toUpperCase()}`,
          value: `${transaction.type === 'deposit' ? '+' : '-'}$${transaction.amount.toLocaleString()}`,
          className: transaction.type === 'deposit' ? 'text-green-500' : 'text-red-500'
        }
      case 'fiat_to_crypto':
        return {
          title: transaction.direction === 'fiattocrypto' 
            ? `Swapped ${transaction.currencyCode.toUpperCase()} to ${transaction.tokenId.toUpperCase()}` 
            : `Swapped ${transaction.tokenId.toUpperCase()} to ${transaction.currencyCode.toUpperCase()}`,
          amount: transaction.direction === 'fiattocrypto' 
            ? `+${transaction.toAmount} ${transaction.tokenId.toUpperCase()}` 
            : `+${transaction.toAmount} ${transaction.currencyCode.toUpperCase()}`,
          value: `$${transaction.toAmount.toLocaleString()}`,
          className: 'text-green-500'
        }
      case 'crypto':
        if (transaction.fromTokenId === transaction.toTokenId) {
          // Transfer of same token
          return {
            title: `Transferred ${transaction.fromTokenId.toUpperCase()}`,
            amount: `${transaction.fromAmount} ${transaction.fromTokenId.toUpperCase()}`,
            value: `-$${transaction.fromAmount.toLocaleString()}`,
            className: 'text-red-500'
          }
        } else {
          // Swap between tokens
          return {
            title: `Swapped ${transaction.fromTokenId.toUpperCase()} to ${transaction.toTokenId.toUpperCase()}`,
            amount: `+${transaction.toAmount} ${transaction.toTokenId.toUpperCase()}`,
            value: transaction.toAmountActual 
              ? `$${transaction.toAmountActual.toLocaleString()}` 
              : `$${transaction.toAmount.toLocaleString()}`,
            className: 'text-muted-foreground'
          }
        }
      default:
        return {
          title: 'Unknown Transaction',
          amount: '',
          value: '',
          className: 'text-muted-foreground'
        }
    }
  }

  if (!mounted) {
    return null
  }

  return (
    <div className="space-y-6">
        <div className="flex flex-col gap-4 md:flex-row">
          <Card className="flex-1">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Balance</CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">$12,122.10</div>
              <p className="text-xs text-muted-foreground">+$1,245.65 (10.3%)</p>
            </CardContent>
          </Card>
          <Card className="flex-1">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Fiat Balance</CardTitle>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                className="h-4 w-4 text-muted-foreground"
              >
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">$5,000.00</div>
              <p className="text-xs text-muted-foreground">Available for trading</p>
            </CardContent>
          </Card>
          <Card className="flex-1">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Crypto Balance</CardTitle>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                className="h-4 w-4 text-muted-foreground"
              >
                <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z" />
                <path d="M16 12l-4-4-4 4M12 16V8" />
              </svg>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">$7,122.10</div>
              <p className="text-xs text-muted-foreground">+$1,245.65 (21.2%)</p>
            </CardContent>
          </Card>
        </div>
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="wallets">Wallets</TabsTrigger>
            <TabsTrigger value="transactions">Transactions</TabsTrigger>
          </TabsList>
          <TabsContent value="overview" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Portfolio Performance</CardTitle>
                <CardDescription>Your portfolio value over the last 12 months</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                <AreaChart
                  data={areaChartData}
                  index="name"
                  categories={["value"]}
                  colors={["primary"]}
                  valueFormatter={(value) => `$${value.toLocaleString()}`}
                  className="h-[300px]"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Asset Allocation</CardTitle>
                <CardDescription>Distribution of your crypto assets</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                <BarChart
                  data={barChartData}
                  index="name"
                  categories={["value"]}
                  colors={["primary"]}
                  valueFormatter={(value) => `$${value.toLocaleString()}`}
                  className="h-[300px]"
                />
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="wallets" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {wallets.map((wallet) => (
                <Card key={wallet.id}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{wallet.name}</CardTitle>
                    <CardDescription>{wallet.symbol}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">${wallet.value.toLocaleString()}</div>
                    <div className="text-sm text-muted-foreground">
                      {wallet.balance} {wallet.symbol}
                    </div>
                    <div
                      className={`mt-2 flex items-center text-sm ${wallet.change >= 0 ? "text-green-500" : "text-red-500"}`}
                    >
                      {wallet.change >= 0 ? (
                        <ArrowUpRight className="mr-1 h-4 w-4" />
                      ) : (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          className="mr-1 h-4 w-4"
                        >
                          <path d="M7 7l5 5 5-5M7 13l5 5 5-5" />
                        </svg>
                      )}
                      {Math.abs(wallet.change)}%
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
          <TabsContent value="transactions" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Recent Transactions</CardTitle>
                <CardDescription>Your recent transactions across all wallets</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-6">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                  </div>
                ) : transactions.length > 0 ? (
                  <div className="space-y-4">
                    {transactions.map((transaction) => {
                      const display = formatTransactionDisplay(transaction);
                      return (
                        <div key={transaction.transactionId} className="flex items-center justify-between border-b pb-4">
                          <div>
                            <div className="font-medium">{display.title}</div>
                            <div className="text-sm text-muted-foreground">{formatDate(transaction.creationDate)}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">{display.amount}</div>
                            <div className={`text-sm ${display.className}`}>{display.value}</div>
                          </div>
                        </div>
                      );
                    })}
                    
                    {/* Pagination Controls */}
                    {pagination.pages > 1 && (
                      <div className="flex items-center justify-between pt-4">
                        <div className="text-sm text-muted-foreground">
                          Showing {transactions.length} of {pagination.total} transactions
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePageChange(pagination.page - 1)}
                            disabled={pagination.page <= 1}
                          >
                            <ChevronLeft className="h-4 w-4" />
                          </Button>
                          <div className="text-sm">
                            Page {pagination.page} of {pagination.pages}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePageChange(pagination.page + 1)}
                            disabled={pagination.page >= pagination.pages}
                          >
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted-foreground">
                    <p>No transactions found</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
  )
}