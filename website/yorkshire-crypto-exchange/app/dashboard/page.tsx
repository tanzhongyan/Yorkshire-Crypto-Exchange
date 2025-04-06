"use client"

import { useState, useEffect, useCallback } from "react"
import { ArrowUpRight, Wallet, CreditCard, Coins, ChevronLeft, ChevronRight } from "lucide-react"
import { getCookie } from "@/lib/cookies"
import axios from "@/lib/axios"
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"

// Define available currencies with their symbols
const FIAT_CURRENCIES = [
  {currencyCode: "usd", name: "US Dollar (USD)", symbol: "$"},
  {currencyCode: "sgd", name: "Singapore Dollar (SGD)", symbol: "S$"},
  {currencyCode: "eur", name: "Euro (EUR)", symbol: "€"},
  {currencyCode: "myr", name: "Malaysian Ringgit (MYR)", symbol: "RM"},
  {currencyCode: "aud", name: "Australian Dollar (AUD)", symbol: "A$"},
  {currencyCode: "gbp", name: "British Pound (GBP)", symbol: "£"},
  {currencyCode: "jpy", name: "Japanese Yen (JPY)", symbol: "¥"},
  {currencyCode: "cny", name: "Chinese Yuan (CNY)", symbol: "¥"},
  {currencyCode: "inr", name: "Indian Rupee (INR)", symbol: "₹"}
];

// Define monochromatic colors for pie chart to match minimalistic design
const COLORS = ["#111111", "#555555", "#999999"]; // Dark, medium, light gray

// Custom tooltip component for pie chart
const CustomPieTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-2 border rounded shadow-sm">
        <p className="font-bold">{data.name}</p>
        <p>Amount: ${data.value.toFixed(2)}</p>
        <p>Price: {data.name === "USDT" ? "$1.00 per USDT" : `$${data.price?.toFixed(2) || '1.00'} per ${data.name === "Crypto" ? "token" : data.tokenId || ''}`}</p>
        <p>Net Worth: ${data.value.toFixed(2)}</p>
        {data.available !== undefined && (
          <p>Available: {data.name === "Fiat" ? `$${data.available.toFixed(2)}` : `${data.availableTokens?.toFixed(8) || data.available.toFixed(2)} ${data.tokenId || ''}`}</p>
        )}
      </div>
    );
  }
  return null;
};

export default function DashboardPage() {
  const [mounted, setMounted] = useState(false)
  const [fiatAccounts, setFiatAccounts] = useState([])
  const [cryptoHoldings, setCryptoHoldings] = useState([])
  const [usdtHolding, setUsdtHolding] = useState(null)
  const [exchangeRates, setExchangeRates] = useState({})
  const [cryptoPrices, setCryptoPrices] = useState({})
  const [transactions, setTransactions] = useState([])
  const [pagination, setPagination] = useState({
    total: 0,
    pages: 0,
    page: 1,
    per_page: 10
  })
  const [loading, setLoading] = useState(false)
  const [loadingBalances, setLoadingBalances] = useState(true)
  const userId = getCookie("userId")

  // Fetch all exchange rates (USD based)
  const fetchAllExchangeRates = useCallback(async () => {
    try {
      // Use axios to call the /market/fiatrates endpoint
      const response = await axios.get('/api/v1/market/fiatrates');
      
      // Check if the response has the expected structure
      if (response.data && response.data.conversion_rates) {
        // Add USD to USD rate (1.0) if not already included
        const rates = { 
          ...response.data.conversion_rates, 
          USD: 1.0 // Ensure USD to USD is 1.0
        };
        setExchangeRates(rates);
      } else {
        console.error("Failed to fetch exchange rates:", response.data);
      }
    } catch (error) {
      console.error("Error fetching exchange rates:", error);
    }
  }, []);

  // Fetch crypto prices from the market/exchangerate endpoint
  const fetchCryptoPrices = useCallback(async (tokenIds) => {
    if (!tokenIds || tokenIds.length === 0) return;
    
    try {
      // Always convert token IDs to uppercase for the API request
      const upperCaseTokens = tokenIds.map(token => token.toUpperCase());
      const tokenString = upperCaseTokens.join(',');
      
      console.log("Fetching prices for tokens:", tokenString);
      
      // Call the exchangerate endpoint
      const response = await axios.get(`/api/v1/market/exchangerate?tokens=${tokenString}`);
      
      if (response.data && response.data.rates) {
        console.log("Received crypto prices:", response.data.rates);
        
        // Store the prices - make sure keys are uppercase for consistent access
        const formattedPrices = {};
        Object.keys(response.data.rates).forEach(key => {
          formattedPrices[key.toUpperCase()] = response.data.rates[key];
        });
        
        setCryptoPrices(formattedPrices);
      } else {
        console.error("Failed to fetch crypto prices:", response.data);
      }
    } catch (error) {
      console.error("Error fetching crypto prices:", error);
    }
  }, []);

  // Calculate total fiat balance in USD (excluding USDT)
  const calculateTotalFiatBalanceUSD = useCallback(() => {
    if (!fiatAccounts.length || !Object.keys(exchangeRates).length) return 0;
    
    return fiatAccounts.reduce((total, account) => {
      const currencyCode = account.currencyCode.toUpperCase();
      const rate = exchangeRates[currencyCode] || 1;
      const valueInUSD = account.balance / rate; // Convert to USD
      return total + valueInUSD;
    }, 0);
  }, [fiatAccounts, exchangeRates]);

  // Get USDT balance in USD
  const getUsdtBalanceUSD = useCallback(() => {
    return usdtHolding ? usdtHolding.actualBalance : 0;
  }, [usdtHolding]);

  // Calculate total crypto balance in USD (excluding USDT)
  const calculateTotalCryptoBalanceUSD = useCallback(() => {
    if (!cryptoHoldings.length) return 0;
    
    // Sum up crypto holdings excluding USDT, using real prices when available
    return cryptoHoldings.reduce((total, holding) => {
      const tokenId = holding.tokenId.toUpperCase();
      // Try to get the price, log when not found
      const price = cryptoPrices[tokenId];
      
      if (price === undefined) {
        console.log(`No price found for ${tokenId}, using default of 1.0`);
        return total + holding.actualBalance; // Default to 1 USD if price not available
      }
      
      return total + (holding.actualBalance * price);
    }, 0);
  }, [cryptoHoldings, cryptoPrices]);

  // Prepare data for pie chart
  const getPieChartData = useCallback(() => {
    const fiatTotal = calculateTotalFiatBalanceUSD();
    const usdtTotal = getUsdtBalanceUSD();
    const usdtAvailable = usdtHolding ? usdtHolding.availableBalance : 0;
    const cryptoTotal = calculateTotalCryptoBalanceUSD();
    
    // Calculate available tokens and total value for each crypto
    const cryptoData = cryptoHoldings.map(holding => {
      const tokenId = holding.tokenId.toUpperCase();
      const price = cryptoPrices[tokenId] || 1;
      const value = holding.actualBalance * price;
      const availableTokens = holding.availableBalance;
      
      return {
        name: tokenId,
        tokenId: tokenId,
        value: value,
        available: holding.availableBalance * price,
        availableTokens: availableTokens,
        price: price
      };
    });
    
    // Calculate aggregate crypto available balance
    const cryptoAvailable = cryptoHoldings.reduce((total, holding) => {
      const tokenId = holding.tokenId.toUpperCase();
      const price = cryptoPrices[tokenId] || 1;
      return total + (holding.availableBalance * price);
    }, 0);
    
    const data = [
      { name: "Fiat", value: fiatTotal, available: fiatTotal }, // For fiat, available = total
      { 
        name: "USDT", 
        tokenId: "USDT", 
        value: usdtTotal, 
        available: usdtAvailable,
        availableTokens: usdtAvailable,
        price: 1
      },
      { 
        name: "Crypto", 
        value: cryptoTotal, 
        available: cryptoAvailable,
        holdings: cryptoData
      }
    ].filter(item => item.value > 0); // Only include non-zero values
    
    return data;
  }, [calculateTotalFiatBalanceUSD, getUsdtBalanceUSD, usdtHolding, calculateTotalCryptoBalanceUSD, cryptoHoldings, cryptoPrices]);

  // Fetch fiat accounts
  const fetchFiatAccounts = useCallback(async () => {
    if (!userId) return;
    
    try {
      const response = await axios.get(`/api/v1/fiat/account/${userId}`);
      setFiatAccounts(response.data);
    } catch (error) {
      console.error("Failed to load fiat accounts:", error);
      setFiatAccounts([]);
    }
  }, [userId]);

  // Fetch crypto holdings
  const fetchCryptoHoldings = useCallback(async () => {
    if (!userId) return;
    
    try {
      // This endpoint returns all crypto holdings for user
      const response = await axios.get(`/api/v1/crypto/holdings/${userId}`);
      
      // If response is successful, extract tokens for price fetching
      if (response.data && Array.isArray(response.data)) {
        console.log("Fetched crypto holdings:", response.data);
        
        // Extract token IDs for price fetching
        const tokenIds = response.data.map(holding => holding.tokenId);
        
        // Filter USDT holding separately
        const usdt = response.data.find(h => h.tokenId.toLowerCase() === 'usdt');
        if (usdt) {
          setUsdtHolding(usdt);
        }
        
        // Set other holdings
        const otherHoldings = response.data.filter(h => h.tokenId.toLowerCase() !== 'usdt');
        setCryptoHoldings(otherHoldings);
        
        // Fetch prices for all tokens
        if (tokenIds.length > 0) {
          await fetchCryptoPrices(tokenIds);
        }
      }
    } catch (error) {
      console.error("Failed to load crypto holdings:", error);
      
      // Try to get USDT specifically as a fallback
      try {
        const usdtResponse = await axios.get(`/api/v1/crypto/holdings/${userId}/usdt`);
        setUsdtHolding(usdtResponse.data);
      } catch (err) {
        console.error("Failed to load USDT holdings:", err);
        setUsdtHolding(null);
      }
      
      setCryptoHoldings([]);
    } finally {
      setLoadingBalances(false);
    }
  }, [userId, fetchCryptoPrices]);

  const fetchTransactions = async (page = 1) => {
    if (!userId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`/api/v1/transaction/aggregated/user/${userId}`, {
        params: {
          page,
          per_page: 10
        }
      });
      
      setTransactions(response.data.transactions);
      setPagination(response.data.pagination);
    } catch (error) {
      console.error("Failed to load transactions:", error);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage) => {
    fetchTransactions(newPage);
  };

  // Initial setup on mount
  useEffect(() => {
    setMounted(true);
  }, []);

  // Load data when component is mounted and userId is available
  useEffect(() => {
    if (mounted && userId) {
      fetchAllExchangeRates();
      fetchFiatAccounts();
      fetchCryptoHoldings();
      fetchTransactions(1);
    }
  }, [mounted, userId, fetchAllExchangeRates, fetchFiatAccounts, fetchCryptoHoldings]);

  // Format dates for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Format currency with proper symbol and decimals
  const formatCurrency = (amount, currencyCode = 'USD') => {
    const currency = FIAT_CURRENCIES.find(c => c.currencyCode.toLowerCase() === currencyCode.toLowerCase());
    const symbol = currency ? currency.symbol : '$';
    
    return `${symbol}${amount.toFixed(2)}`;
  };

  // Format transaction amount for display
  const formatTransactionDisplay = (transaction) => {
    switch (transaction.transactionType) {
      case 'fiat':
        return {
          title: transaction.type === 'deposit' 
            ? `Deposited ${transaction.currencyCode.toUpperCase()}` 
            : `Withdrew ${transaction.currencyCode.toUpperCase()}`,
          amount: `${transaction.type === 'deposit' ? '+' : '-'}${transaction.amount} ${transaction.currencyCode.toUpperCase()}`,
          value: `${transaction.type === 'deposit' ? '+' : '-'}$${parseFloat(transaction.amount).toFixed(2)}`,
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
          value: `$${parseFloat(transaction.toAmount).toFixed(2)}`,
          className: 'text-green-500'
        }
      case 'crypto':
        if (transaction.fromTokenId === transaction.toTokenId) {
          // Transfer of same token
          return {
            title: `Transferred ${transaction.fromTokenId.toUpperCase()}`,
            amount: `${transaction.fromAmount} ${transaction.fromTokenId.toUpperCase()}`,
            value: `-$${parseFloat(transaction.fromAmount).toFixed(2)}`,
            className: 'text-red-500'
          }
        } else {
          // Swap between tokens
          return {
            title: `Swapped ${transaction.fromTokenId.toUpperCase()} to ${transaction.toTokenId.toUpperCase()}`,
            amount: `+${transaction.toAmount} ${transaction.toTokenId.toUpperCase()}`,
            value: transaction.toAmountActual 
              ? `$${parseFloat(transaction.toAmountActual).toFixed(2)}` 
              : `$${parseFloat(transaction.toAmount).toFixed(2)}`,
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
  };

  // Custom renderer for pie chart labels
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text x={x} y={y} fill="white" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  if (!mounted) {
    return null;
  }

  // Calculate balances
  const totalFiatBalanceUSD = calculateTotalFiatBalanceUSD();
  const usdtBalanceUSD = getUsdtBalanceUSD();
  const totalCryptoBalanceUSD = calculateTotalCryptoBalanceUSD();
  const totalBalanceUSD = totalFiatBalanceUSD + usdtBalanceUSD + totalCryptoBalanceUSD;
  
  // Prepare pie chart data
  const pieChartData = getPieChartData();

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Balance (USD)</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalBalanceUSD.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">All values calculated in USD</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Fiat Balance (USD)</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalFiatBalanceUSD.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">Traditional currencies</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">USDT Balance</CardTitle>
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
              <path d="M12 8v8m-4-4h8" />
            </svg>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${usdtBalanceUSD.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              Available: ${usdtHolding ? usdtHolding.availableBalance.toFixed(2) : "0.00"}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Crypto Balance (USD)</CardTitle>
            <Coins className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalCryptoBalanceUSD.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">Excluding USDT</p>
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
              <CardTitle>Asset Allocation</CardTitle>
              <CardDescription>Distribution of your assets (all values in USD)</CardDescription>
            </CardHeader>
            <CardContent>
              {loadingBalances ? (
                <div className="flex justify-center py-6">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Pie Chart - Made bigger */}
                  <div style={{ height: '550px', width: '100%' }}>
                    {pieChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieChartData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={renderCustomizedLabel}
                            outerRadius={160} // Increased size
                            fill="#8884d8"
                            dataKey="value"
                          >
                            {pieChartData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip content={<CustomPieTooltip />} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="text-center text-muted-foreground h-full flex items-center justify-center">
                        <p>No assets to display</p>
                      </div>
                    )}
                  </div>
                  
                  {/* Asset Details */}
                  <div className="space-y-6">
                    {/* Fiat Balances */}
                    <div>
                      <h3 className="text-sm font-medium mb-2">Fiat Currencies</h3>
                      <div className="space-y-2">
                        {fiatAccounts.length > 0 ? (
                          fiatAccounts.map((account) => {
                            const currencyCode = account.currencyCode.toUpperCase();
                            const rate = exchangeRates[currencyCode] || 1;
                            const valueInUSD = account.balance / rate;
                            
                            return (
                              <div key={account.currencyCode} className="flex justify-between items-center p-2 rounded-md border">
                                <div>
                                  <div className="font-medium">{account.currencyCode.toUpperCase()}</div>
                                  <div className="text-sm text-muted-foreground">
                                    {formatCurrency(account.balance, account.currencyCode)}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className="font-medium">
                                    ${valueInUSD.toFixed(2)}
                                  </div>
                                  <div className="text-sm text-muted-foreground">
                                    Rate: ${(currencyCode === "USD") ? "1.00" : (1/rate).toFixed(6)}
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        ) : (
                          <div className="text-center py-4 text-muted-foreground">
                            <p>No fiat accounts found</p>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* USDT Balance */}
                    <div>
                      <h3 className="text-sm font-medium mb-2">USDT</h3>
                      <div className="space-y-2">
                        {usdtHolding ? (
                          <div className="flex justify-between items-center p-2 rounded-md border">
                            <div>
                              <div className="font-medium">USDT</div>
                              <div className="text-sm text-muted-foreground">
                                {usdtHolding.actualBalance.toFixed(2)} USDT
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-medium">
                                ${usdtHolding.actualBalance.toFixed(2)}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                Available: {usdtHolding.availableBalance.toFixed(2)} USDT • Rate: $1.00
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-4 text-muted-foreground">
                            <p>No USDT holdings found</p>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Other Crypto Balances */}
                    <div>
                      <h3 className="text-sm font-medium mb-2">Other Cryptocurrencies</h3>
                      <div className="space-y-2">
                        {cryptoHoldings.length > 0 ? (
                          cryptoHoldings.map((holding) => {
                            const tokenId = holding.tokenId.toUpperCase();
                            const price = cryptoPrices[tokenId];
                            const valueInUSD = holding.actualBalance * (price || 1);
                            
                            return (
                              <div key={holding.tokenId} className="flex justify-between items-center p-2 rounded-md border">
                                <div>
                                  <div className="font-medium">{tokenId}</div>
                                  <div className="text-sm text-muted-foreground">
                                    {holding.actualBalance.toFixed(8)} {tokenId}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className="font-medium">
                                    ${valueInUSD.toFixed(2)}
                                  </div>
                                  <div className="text-sm text-muted-foreground">
                                    Available: {holding.availableBalance.toFixed(8)} {tokenId} • Price: ${price ? price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "1.00"}
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        ) : (
                          <div className="text-center py-4 text-muted-foreground">
                            <p>No other crypto holdings found</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="wallets" className="space-y-4">
          {loadingBalances ? (
            <div className="flex justify-center py-6">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Fiat Wallets Section */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Fiat Accounts</h3>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  {fiatAccounts.length > 0 ? (
                    fiatAccounts.map((account) => {
                      const currencyCode = account.currencyCode.toUpperCase();
                      const rate = exchangeRates[currencyCode] || 1;
                      const valueInUSD = account.balance / rate;
                      const currency = FIAT_CURRENCIES.find(c => c.currencyCode.toLowerCase() === account.currencyCode.toLowerCase());
                      
                      return (
                        <Card key={account.currencyCode}>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-base">{currencyCode}</CardTitle>
                            <CardDescription>{currency?.name || currencyCode}</CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold">
                              {formatCurrency(account.balance, account.currencyCode)}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              ${valueInUSD.toFixed(2)} USD
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })
                  ) : (
                    <div className="col-span-full text-center py-4 text-muted-foreground">
                      <p>No fiat accounts found</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* USDT Section */}
              <div>
                <h3 className="text-lg font-semibold mb-2">USDT</h3>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  {usdtHolding ? (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">USDT</CardTitle>
                        <CardDescription>Tether</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">
                          {usdtHolding.actualBalance.toFixed(2)} USDT
                        </div>
                        <div className="text-sm text-muted-foreground">
                          ${usdtHolding.actualBalance.toFixed(2)} USD • Rate: $1.00
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          Available: {usdtHolding.availableBalance.toFixed(2)} USDT
                        </div>
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="col-span-full text-center py-4 text-muted-foreground">
                      <p>No USDT holdings found</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Other Crypto Section */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Other Cryptocurrencies</h3>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  {cryptoHoldings.length > 0 ? (
                    cryptoHoldings.map((holding) => {
                      const tokenId = holding.tokenId.toUpperCase();
                      const price = cryptoPrices[tokenId];
                      const valueInUSD = holding.actualBalance * (price || 1);
                      
                      return (
                        <Card key={holding.tokenId}>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-base">{tokenId}</CardTitle>
                            <CardDescription>Cryptocurrency</CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold">
                              {holding.actualBalance.toFixed(8)} {tokenId}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              ${valueInUSD.toFixed(2)} USD • Price: ${price ? price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "1.00"}
                            </div>
                            <div className="text-sm text-muted-foreground mt-1">
                              Available: {holding.availableBalance.toFixed(8)} {tokenId}
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })
                  ) : (
                    <div className="col-span-full text-center py-4 text-muted-foreground">
                      <p>No other crypto holdings found</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
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