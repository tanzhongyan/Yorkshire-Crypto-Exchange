"use client"

import type React from "react"
import { useState, useEffect, useCallback } from "react"
import { ArrowUp, ArrowDown, RefreshCw, X } from "lucide-react"
import axios from "@/lib/axios"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { getCookie } from "@/lib/cookies"

export default function BuyPage() {
  // User state
  const userId = getCookie("userId") || ""
  
  // Order state
  const [orderType, setOrderType] = useState("limit")
  const [buyPrice, setBuyPrice] = useState("65000.00")
  const [buyAmount, setBuyAmount] = useState("")
  const [buyUsdtAmount, setBuyUsdtAmount] = useState("")
  const [buyFeeRate, setBuyFeeRate] = useState(0.05) // 5% default fee
  const [sellPrice, setSellPrice] = useState("65100.00")
  const [sellAmount, setSellAmount] = useState("")
  const [sellFeeRate, setSellFeeRate] = useState(0.05) // 5% default fee
  const [isProcessing, setIsProcessing] = useState(false)
  
  // Notification state
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" })
  
  // Market data state
  const [availableTokens, setAvailableTokens] = useState([])
  const [selectedPair, setSelectedPair] = useState("BTC/USDT")
  const [currentToken, setCurrentToken] = useState("btc")
  const [orderBook, setOrderBook] = useState({ asks: [], bids: [] })
  const [recentTrades, setRecentTrades] = useState([])
  const [currentPrice, setCurrentPrice] = useState(65100)
  
  // Balance state
  const [usdtBalance, setUsdtBalance] = useState({ available: 0, actual: 0 })
  const [tokenBalance, setTokenBalance] = useState({ available: 0, actual: 0 })
  
  // Transactions state
  const [transactions, setTransactions] = useState([])
  const [allTransactions, setAllTransactions] = useState([])
  const [loadingTransactions, setLoadingTransactions] = useState(true)
  const [loadingAllTransactions, setLoadingAllTransactions] = useState(true)

  // Calculate totals
  const buyTotal = buyPrice && buyAmount ? (Number.parseFloat(buyPrice) * Number.parseFloat(buyAmount)).toFixed(2) : "0.00"
  const sellTotal = sellPrice && sellAmount ? (Number.parseFloat(sellPrice) * Number.parseFloat(sellAmount)).toFixed(2) : "0.00"
  
  // Calculate fees
  const buyFee = buyPrice && buyAmount ? (Number.parseFloat(buyTotal) * buyFeeRate).toFixed(2) : "0.00"
  const sellFee = sellPrice && sellAmount ? (Number.parseFloat(sellTotal) * sellFeeRate).toFixed(2) : "0.00"

  // Show notification
  const showNotification = (message, type = "success") => {
    setNotification({ show: true, message, type })
    
    // Auto hide after 5 seconds
    setTimeout(() => {
      setNotification({ show: false, message: "", type: "success" })
    }, 5000)
  }

  // Fetch exchange rate for current token - fixed to properly handle token case
  const fetchExchangeRate = useCallback(async (token) => {
    if (!token) return
    
    try {
      // Use lowercase for API request as standardized in backend
      const tokenLower = token.toLowerCase()
      const response = await axios.get(`/api/v1/market/exchangerate?tokens=${tokenLower}`)
      
      // Check if response contains rates for the token (in lowercase)
      if (response.data && response.data.rates && response.data.rates[tokenLower] !== undefined) {
        const rate = response.data.rates[tokenLower]
        setCurrentPrice(rate)
        
        // Update buy/sell prices with latest rate
        const formattedRate = rate.toFixed(2)
        setBuyPrice(formattedRate)
        setSellPrice(formattedRate)
      }
    } catch (error) {
      console.error("Failed to fetch exchange rate:", error)
    }
  }, [])

  // Fetch available tokens
  const fetchAvailableTokens = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/crypto/token')
      const tokens = response.data.filter(token => token.tokenId.toLowerCase() !== 'usdt')
      setAvailableTokens(tokens)
      
      // Set default token if none selected yet
      if (!currentToken && tokens.length > 0) {
        const defaultToken = tokens[0].tokenId.toLowerCase()
        setCurrentToken(defaultToken)
        setSelectedPair(`${tokens[0].tokenId.toUpperCase()}/USDT`)
        fetchExchangeRate(defaultToken)
      }
    } catch (error) {
      console.error("Failed to fetch tokens:", error)
    }
  }, [currentToken, fetchExchangeRate])

  // Fetch order book data
  const fetchOrderBook = useCallback(async () => {
    if (!currentToken) return
    
    try {
      const response = await axios.get(`/api/v1/orderbook/sortedorders?token=${currentToken.toLowerCase()}`)
      setOrderBook({
        asks: response.data.sell || [],
        bids: response.data.buy || []
      })
    } catch (error) {
      console.error("Failed to fetch order book:", error)
    }
  }, [currentToken])

  // Fetch recent trades
  const fetchRecentTrades = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/orderbook/recentorders')
      
      // Filter for current token if needed
      const filteredTrades = response.data.orders.filter(order => 
        (order.fromTokenId.toLowerCase() === currentToken.toLowerCase() && order.toTokenId.toLowerCase() === 'usdt') ||
        (order.fromTokenId.toLowerCase() === 'usdt' && order.toTokenId.toLowerCase() === currentToken.toLowerCase())
      )
      
      // Format trades data
      const formattedTrades = filteredTrades.map(order => ({
        price: order.limitPrice,
        amount: order.fromTokenId.toLowerCase() === 'usdt' 
          ? order.toAmount || order.fromAmount / order.limitPrice
          : order.fromAmount || order.toAmount / order.limitPrice,
        time: new Date(order.creation).toLocaleTimeString(),
        type: order.fromTokenId.toLowerCase() === 'usdt' ? 'buy' : 'sell'
      }))
      
      // Limit to 12 trades as requested
      setRecentTrades(formattedTrades.slice(0, 12))
    } catch (error) {
      console.error("Failed to fetch recent trades:", error)
    }
  }, [currentToken])

  // Fetch balances
  const fetchBalances = useCallback(async () => {
    if (!userId) return
    
    try {
      // Fetch USDT balance
      const usdtResponse = await axios.get(`/api/v1/crypto/holdings/${userId}/usdt`)
      setUsdtBalance({
        available: usdtResponse.data.availableBalance,
        actual: usdtResponse.data.actualBalance
      })
      
      // Fetch selected token balance if not USDT
      if (currentToken !== 'usdt') {
        const tokenResponse = await axios.get(`/api/v1/crypto/holdings/${userId}/${currentToken}`)
        setTokenBalance({
          available: tokenResponse.data.availableBalance,
          actual: tokenResponse.data.actualBalance
        })
      }
    } catch (error) {
      console.error("Failed to fetch balances:", error)
      // Set default values if balance not found
      if (error.response && error.response.status === 404) {
        if (currentToken !== 'usdt') {
          setTokenBalance({ available: 0, actual: 0 })
        }
      }
    }
  }, [userId, currentToken])

  // Fetch transactions for current pair
  const fetchTransactions = useCallback(async () => {
    if (!userId) return
    
    setLoadingTransactions(true)
    try {
      const response = await axios.get(`/api/v1/transaction/crypto/user/${userId}`)
      
      // Filter transactions for the current trading pair
      const filteredTransactions = response.data.filter(tx => 
        (tx.fromTokenId.toLowerCase() === currentToken.toLowerCase() && tx.toTokenId.toLowerCase() === 'usdt') ||
        (tx.fromTokenId.toLowerCase() === 'usdt' && tx.toTokenId.toLowerCase() === currentToken.toLowerCase())
      )
      
      setTransactions(filteredTransactions)
    } catch (error) {
      console.error("Failed to fetch transactions:", error)
    } finally {
      setLoadingTransactions(false)
    }
  }, [userId, currentToken])
  
  // Fetch all transactions
  const fetchAllTransactions = useCallback(async () => {
    if (!userId) return
    
    setLoadingAllTransactions(true)
    try {
      const response = await axios.get(`/api/v1/transaction/crypto/user/${userId}`)
      setAllTransactions(response.data)
    } catch (error) {
      console.error("Failed to fetch all transactions:", error)
    } finally {
      setLoadingAllTransactions(false)
    }
  }, [userId])

  // Handle pair change
  const handlePairChange = (newPair) => {
    const [token] = newPair.split('/')
    setSelectedPair(newPair)
    const newToken = token.toLowerCase()
    setCurrentToken(newToken)
    fetchExchangeRate(newToken)
  }

  // Handle buy price change
  const handleBuyPriceChange = (e) => {
    const newPrice = e.target.value
    setBuyPrice(newPrice)
    
    // If USDT amount is set, recalculate token amount
    if (buyUsdtAmount) {
      const tokenAmount = Number.parseFloat(buyUsdtAmount) / Number.parseFloat(newPrice || 1)
      setBuyAmount(tokenAmount.toFixed(6))
    }
  }
  
  // Handle buy USDT amount change
  const handleBuyUsdtAmountChange = (e) => {
    const newUsdtAmount = e.target.value
    setBuyUsdtAmount(newUsdtAmount)
    
    // Calculate token amount based on USDT and price
    if (newUsdtAmount && buyPrice) {
      const tokenAmount = Number.parseFloat(newUsdtAmount) / Number.parseFloat(buyPrice)
      setBuyAmount(tokenAmount.toFixed(6))
    } else {
      setBuyAmount("")
    }
  }
  
  // Handle buy amount change
  const handleBuyAmountChange = (e) => {
    const newAmount = e.target.value
    setBuyAmount(newAmount)
    
    // Calculate USDT amount based on token amount and price
    if (newAmount && buyPrice) {
      const usdtAmount = Number.parseFloat(newAmount) * Number.parseFloat(buyPrice)
      setBuyUsdtAmount(usdtAmount.toFixed(2))
    } else {
      setBuyUsdtAmount("")
    }
  }

  // Place buy order
  const handleBuySubmit = async (e) => {
    e.preventDefault()
    
    if (!userId || !buyAmount || Number.parseFloat(buyAmount) <= 0) {
      return
    }
    
    setIsProcessing(true)
    
    const buyTotalAmount = Number.parseFloat(buyUsdtAmount || buyTotal)
    const tokenAmount = Number.parseFloat(buyAmount)
    const price = Number.parseFloat(buyPrice)
    
    const orderData = {
      userId: userId,
      fromTokenId: 'usdt',               // Buy: from USDT
      fromAmount: buyTotalAmount,        // Total USDT amount
      toTokenId: currentToken,           // Buy: to the selected token
      toAmount: tokenAmount,             // Amount of tokens to buy
      limitPrice: price,                 // Price per token
      orderType: orderType               // Limit or Market
    }
    
    try {
      const response = await axios.post('/api/v1/order/create_order', orderData)
      
      // Show success notification instead of alert
      showNotification(`Buy order placed successfully: ${buyAmount} ${currentToken.toUpperCase()} at $${buyPrice}`)
      
      setBuyAmount("")
      setBuyUsdtAmount("")
      
      // Refresh data
      fetchBalances()
      fetchOrderBook()
      fetchRecentTrades()
      fetchTransactions()
      fetchAllTransactions()
    } catch (error) {
      console.error("Buy order failed:", error)
      showNotification(`Buy order failed: ${error.response?.data?.error || "Unknown error"}`, "error")
    } finally {
      setIsProcessing(false)
    }
  }

  // Place sell order
  const handleSellSubmit = async (e) => {
    e.preventDefault()
    
    if (!userId || !sellAmount || Number.parseFloat(sellAmount) <= 0) {
      return
    }
    
    setIsProcessing(true)
    
    const tokenAmount = Number.parseFloat(sellAmount)
    const usdtAmount = Number.parseFloat(sellTotal)
    const price = Number.parseFloat(sellPrice)
    
    const orderData = {
      userId: userId,
      fromTokenId: currentToken,         // Sell: from the selected token
      fromAmount: tokenAmount,           // Amount of tokens to sell
      toTokenId: 'usdt',                 // Sell: to USDT
      toAmount: usdtAmount,              // Total USDT amount
      limitPrice: price,                 // Price per token
      orderType: orderType               // Limit or Market
    }
    
    try {
      const response = await axios.post('/api/v1/order/create_order', orderData)
      
      // Show success notification instead of alert
      showNotification(`Sell order placed successfully: ${sellAmount} ${currentToken.toUpperCase()} at $${sellPrice}`)
      
      setSellAmount("")
      
      // Refresh data
      fetchBalances()
      fetchOrderBook()
      fetchRecentTrades()
      fetchTransactions()
      fetchAllTransactions()
    } catch (error) {
      console.error("Sell order failed:", error)
      showNotification(`Sell order failed: ${error.response?.data?.error || "Unknown error"}`, "error")
    } finally {
      setIsProcessing(false)
    }
  }

  // Initialize data
  useEffect(() => {
    fetchAvailableTokens()
    fetchAllTransactions()
  }, [fetchAvailableTokens, fetchAllTransactions])

  // Update data when token changes
  useEffect(() => {
    if (currentToken) {
      fetchOrderBook()
      fetchRecentTrades()
      fetchBalances()
      fetchTransactions()
    }
  }, [currentToken, fetchOrderBook, fetchRecentTrades, fetchBalances, fetchTransactions])

  // Periodic data refresh - refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchOrderBook()
      fetchRecentTrades()
      fetchExchangeRate(currentToken)
    }, 5000)
    
    return () => clearInterval(interval)
  }, [fetchOrderBook, fetchRecentTrades, fetchExchangeRate, currentToken])

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Notification popup */}
      {notification.show && (
        <div className={`fixed top-4 right-4 z-50 max-w-md p-4 rounded-lg shadow-lg ${
          notification.type === "success" ? "bg-green-100 border border-green-400" : "bg-red-100 border border-red-400"
        }`}>
          <div className="flex items-start justify-between">
            <div className={`text-sm font-medium ${
              notification.type === "success" ? "text-green-800" : "text-red-800"
            }`}>
              {notification.message}
            </div>
            <button
              onClick={() => setNotification({ ...notification, show: false })}
              className="ml-4 inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
      
      <div className="lg:col-span-2 space-y-6">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{selectedPair}</CardTitle>
                <CardDescription>{currentToken.toUpperCase()} to Tether</CardDescription>
              </div>
              <Select value={selectedPair} onValueChange={handlePairChange}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Select pair" />
                </SelectTrigger>
                <SelectContent>
                  {availableTokens.map((token) => (
                    <SelectItem key={token.tokenId} value={`${token.tokenId.toUpperCase()}/USDT`}>
                      {token.tokenId.toUpperCase()}/USDT
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${currentPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Order Book</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="grid grid-cols-3 text-xs font-medium text-muted-foreground mb-2">
                    <div>Price (USDT)</div>
                    <div className="text-right">Amount ({currentToken.toUpperCase()})</div>
                    <div className="text-right">Total (USDT)</div>
                  </div>
                  <div className="space-y-1">
                    {orderBook.asks.length > 0 ? (
                      orderBook.asks.map((ask, index) => (
                        <div key={index} className="grid grid-cols-3 text-xs text-red-500">
                          <div>{ask.limitPrice?.toFixed(2) || 0}</div>
                          <div className="text-right">{ask.fromAmount?.toFixed(6) || 0}</div>
                          <div className="text-right">{(ask.limitPrice * ask.fromAmount)?.toFixed(2) || 0}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-xs text-muted-foreground py-2">No sell orders</div>
                    )}
                  </div>
                </div>

                <div className="py-2 text-center font-bold text-lg">${currentPrice.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>

                <div>
                  <div className="space-y-1">
                    {orderBook.bids.length > 0 ? (
                      orderBook.bids.map((bid, index) => (
                        <div key={index} className="grid grid-cols-3 text-xs text-green-500">
                          <div>{bid.limitPrice?.toFixed(2) || 0}</div>
                          <div className="text-right">{bid.toAmount?.toFixed(6) || (bid.fromAmount / bid.limitPrice)?.toFixed(6) || 0}</div>
                          <div className="text-right">{bid.fromAmount?.toFixed(2) || 0}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-xs text-muted-foreground py-2">No buy orders</div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Trades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-4 text-xs font-medium text-muted-foreground mb-2">
                  <div>Price (USDT)</div>
                  <div className="text-right">Amount ({currentToken.toUpperCase()})</div>
                  <div className="text-right">Total (USDT)</div>
                  <div className="text-right">Time</div>
                </div>
                <div className="space-y-2">
                  {recentTrades.length > 0 ? (
                    recentTrades.map((trade, index) => (
                      <div
                        key={index}
                        className={`grid grid-cols-4 text-xs ${trade.type === "buy" ? "text-green-500" : "text-red-500"}`}
                      >
                        <div>{trade.price.toFixed(2)}</div>
                        <div className="text-right">{trade.amount.toFixed(6)}</div>
                        <div className="text-right">{(trade.price * trade.amount).toFixed(2)}</div>
                        <div className="text-right">{trade.time}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-xs text-muted-foreground py-2">No recent trades</div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>Transaction History</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="current-pair">
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="current-pair">Current Pair</TabsTrigger>
                <TabsTrigger value="all-transactions">All Transactions</TabsTrigger>
              </TabsList>
              
              <TabsContent value="current-pair">
                {loadingTransactions ? (
                  <div className="flex justify-center py-4">
                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : transactions.length > 0 ? (
                  <div className="space-y-2 max-h-80 overflow-y-auto">
                    {transactions.map((tx) => (
                      <div key={tx.transactionId} className="border rounded-md p-3">
                        <div className="flex justify-between items-center mb-2">
                          <div className="text-sm font-medium">
                            {tx.fromTokenId.toLowerCase() === 'usdt' ? 'Buy' : 'Sell'} {tx.fromTokenId.toLowerCase() === 'usdt' ? tx.toTokenId.toUpperCase() : tx.fromTokenId.toUpperCase()}
                          </div>
                          <div className={`text-xs px-2 py-1 rounded-full ${tx.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                            {tx.status}
                          </div>
                        </div>
                        <div className="grid grid-cols-3 text-xs gap-1">
                          <div>
                            <div className="text-muted-foreground">Amount</div>
                            <div>{tx.fromTokenId.toLowerCase() === 'usdt' ? tx.toAmount : tx.fromAmount} {tx.fromTokenId.toLowerCase() === 'usdt' ? tx.toTokenId.toUpperCase() : tx.fromTokenId.toUpperCase()}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Price</div>
                            <div>${tx.limitPrice.toFixed(2)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Total</div>
                            <div>${tx.fromTokenId.toLowerCase() === 'usdt' ? tx.fromAmount.toFixed(2) : tx.toAmount.toFixed(2)}</div>
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {new Date(tx.creation).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No transactions for this trading pair
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="all-transactions">
                {loadingAllTransactions ? (
                  <div className="flex justify-center py-4">
                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : allTransactions.length > 0 ? (
                  <div className="space-y-2 max-h-80 overflow-y-auto">
                    {allTransactions.map((tx) => (
                      <div key={tx.transactionId} className="border rounded-md p-3">
                        <div className="flex justify-between items-center mb-2">
                          <div className="text-sm font-medium">
                            {tx.fromTokenId.toLowerCase() === 'usdt' ? 'Buy' : 'Sell'} {tx.fromTokenId.toLowerCase() === 'usdt' ? tx.toTokenId.toUpperCase() : tx.fromTokenId.toUpperCase()}
                          </div>
                          <div className={`text-xs px-2 py-1 rounded-full ${tx.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                            {tx.status}
                          </div>
                        </div>
                        <div className="grid grid-cols-3 text-xs gap-1">
                          <div>
                            <div className="text-muted-foreground">Amount</div>
                            <div>{tx.fromTokenId.toLowerCase() === 'usdt' ? tx.toAmount : tx.fromAmount} {tx.fromTokenId.toLowerCase() === 'usdt' ? tx.toTokenId.toUpperCase() : tx.fromTokenId.toUpperCase()}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Price</div>
                            <div>${tx.limitPrice.toFixed(2)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Total</div>
                            <div>${tx.fromTokenId.toLowerCase() === 'usdt' ? tx.fromAmount.toFixed(2) : tx.toAmount.toFixed(2)}</div>
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {new Date(tx.creation).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No transactions found
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <div>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Place Order</CardTitle>
            <CardDescription>Enter your order details below</CardDescription>
            <div className="flex space-x-2 mt-2">
              <Button
                variant={orderType === "limit" ? "default" : "outline"}
                size="sm"
                onClick={() => setOrderType("limit")}
              >
                Limit Order
              </Button>
              <Button
                variant={orderType === "market" ? "default" : "outline"}
                size="sm"
                onClick={() => setOrderType("market")}
              >
                Market Order
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="buy">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="buy">Buy</TabsTrigger>
                <TabsTrigger value="sell">Sell</TabsTrigger>
                <TabsTrigger value="fee">Fee</TabsTrigger>
              </TabsList>
              
              <TabsContent value="buy" className="space-y-4 pt-4">
                <form onSubmit={handleBuySubmit}>
                  <div className="space-y-4">
                    {orderType === "limit" && (
                      <div className="space-y-2">
                        <Label htmlFor="buy-price">Price per {currentToken.toUpperCase()} (USDT)</Label>
                        <Input
                          id="buy-price"
                          type="number"
                          step="0.01"
                          value={buyPrice}
                          onChange={handleBuyPriceChange}
                          required
                        />
                      </div>
                    )}
                    
                    <div className="space-y-2">
                      <Label htmlFor="buy-usdt-amount">USDT Amount to Spend</Label>
                      <Input
                        id="buy-usdt-amount"
                        type="number"
                        step="0.01"
                        placeholder="0.00"
                        value={buyUsdtAmount}
                        onChange={handleBuyUsdtAmountChange}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="buy-amount">Amount of {currentToken.toUpperCase()} to Buy</Label>
                      <Input
                        id="buy-amount"
                        type="number"
                        step="0.0001"
                        placeholder="0.00"
                        value={buyAmount}
                        onChange={handleBuyAmountChange}
                        required
                      />
                    </div>
                    <Separator />
                    
                    <div className="flex justify-between items-center">
                      <div className="text-sm">
                        <div className="text-muted-foreground">Total Order</div>
                        <div className="font-medium">{(buyUsdtAmount || buyTotal)} USDT</div>
                        <div className="text-muted-foreground mt-1">Fee (5%)</div>
                        <div className="font-medium">{buyFee} USDT</div>
                      </div>
                      
                      <div className="text-xs text-right">
                        <div className="text-muted-foreground">Available Balance</div>
                        <div>{usdtBalance.available.toFixed(2)} USDT</div>
                        <div className="text-muted-foreground mt-1">Actual Balance</div>
                        <div>{usdtBalance.actual.toFixed(2)} USDT</div>
                      </div>
                    </div>
                    
                    <Button 
                      type="submit" 
                      className="w-full bg-green-600 hover:bg-green-700"
                      disabled={isProcessing || !buyAmount || Number.parseFloat(buyAmount) <= 0 || 
                              Number.parseFloat(buyUsdtAmount || buyTotal) > usdtBalance.available}
                    >
                      {isProcessing ? (
                        <div className="flex items-center">
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> Processing...
                        </div>
                      ) : (
                        `Buy ${currentToken.toUpperCase()}`
                      )}
                    </Button>
                  </div>
                </form>
              </TabsContent>
              
              <TabsContent value="sell" className="space-y-4 pt-4">
                <form onSubmit={handleSellSubmit}>
                  <div className="space-y-4">
                    {orderType === "limit" && (
                      <div className="space-y-2">
                        <Label htmlFor="sell-price">Price per {currentToken.toUpperCase()} (USDT)</Label>
                        <Input
                          id="sell-price"
                          type="number"
                          step="0.01"
                          value={sellPrice}
                          onChange={(e) => setSellPrice(e.target.value)}
                          required
                        />
                      </div>
                    )}
                    <div className="space-y-2">
                      <Label htmlFor="sell-amount">Amount of {currentToken.toUpperCase()} to Sell</Label>
                      <Input
                        id="sell-amount"
                        type="number"
                        step="0.0001"
                        placeholder="0.00"
                        value={sellAmount}
                        onChange={(e) => setSellAmount(e.target.value)}
                        required
                      />
                    </div>
                    <Separator />
                    
                    <div className="flex justify-between items-center">
                      <div className="text-sm">
                        <div className="text-muted-foreground">Total Order</div>
                        <div className="font-medium">{sellTotal} USDT</div>
                        <div className="text-muted-foreground mt-1">Fee (5%)</div>
                        <div className="font-medium">{sellFee} USDT</div>
                      </div>
                      
                      <div className="text-xs text-right">
                        <div className="text-muted-foreground">Available Balance</div>
                        <div>{tokenBalance.available.toFixed(6)} {currentToken.toUpperCase()}</div>
                        <div className="text-muted-foreground mt-1">Actual Balance</div>
                        <div>{tokenBalance.actual.toFixed(6)} {currentToken.toUpperCase()}</div>
                      </div>
                    </div>
                    
                    <Button 
                      type="submit" 
                      className="w-full bg-red-600 hover:bg-red-700"
                      disabled={isProcessing || !sellAmount || Number.parseFloat(sellAmount) <= 0 || 
                                Number.parseFloat(sellAmount) > tokenBalance.available}
                    >
                      {isProcessing ? (
                        <div className="flex items-center">
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> Processing...
                        </div>
                      ) : (
                        `Sell ${currentToken.toUpperCase()}`
                      )}
                    </Button>
                  </div>
                </form>
              </TabsContent>
              
              <TabsContent value="fee" className="pt-4">
                <div className="space-y-4">
                  <div className="text-sm space-y-2">
                    <h3 className="font-medium">Fee Structure</h3>
                    <p>Our standard trading fee is <strong>5%</strong> of the transaction value.</p>
                    
                    <div className="mt-4">
                      <div className="grid grid-cols-2 gap-2 text-sm border-b pb-2">
                        <div className="font-medium">Trade Type</div>
                        <div className="font-medium text-right">Fee Rate</div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm py-2 border-b">
                        <div>Buy Orders</div>
                        <div className="text-right">5%</div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm py-2 border-b">
                        <div>Sell Orders</div>
                        <div className="text-right">5%</div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm py-2">
                        <div>Market Orders</div>
                        <div className="text-right">5%</div>
                      </div>
                    </div>
                    
                    <p className="mt-4 text-xs text-muted-foreground">
                      Fees are automatically calculated and included in your order total.
                      Higher trading volumes may qualify for reduced fees.
                    </p>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}