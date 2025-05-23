"use client";

import type React from "react";
import { useState, useEffect, useCallback } from "react";
import { RefreshCw, X, Info } from "lucide-react";
import axios from "@/lib/axios";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getCookie } from "@/lib/cookies";

export default function BuyPage() {
  // User state
  const userId = getCookie("userId") || "";

  // Order state
  const [orderType, setOrderType] = useState("limit");
  const [buyPrice, setBuyPrice] = useState("");
  const [buyAmount, setBuyAmount] = useState("");
  const [buyUsdtAmount, setBuyUsdtAmount] = useState("");
  const [sellPrice, setSellPrice] = useState("");
  const [sellAmount, setSellAmount] = useState("");
  const [sellUsdtAmount, setSellUsdtAmount] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  // Notification state
  const [notification, setNotification] = useState({
    show: false,
    message: "",
    type: "success",
  });

  // Market data state
  const [availableTokens, setAvailableTokens] = useState([]);
  const [selectedPair, setSelectedPair] = useState("");
  const [currentToken, setCurrentToken] = useState("");
  const [orderBook, setOrderBook] = useState({ asks: [], bids: [] });
  const [recentTrades, setRecentTrades] = useState([]);
  const [currentPrice, setCurrentPrice] = useState(0);

  // Balance state
  const [usdtBalance, setUsdtBalance] = useState({ available: 0, actual: 0 });
  const [tokenBalance, setTokenBalance] = useState({ available: 0, actual: 0 });

  // Transactions state
  const [transactions, setTransactions] = useState([]);
  const [allTransactions, setAllTransactions] = useState([]);
  const [loadingTransactions, setLoadingTransactions] = useState(true);
  const [loadingAllTransactions, setLoadingAllTransactions] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);

  // Track user modifications
  const [buyPriceModified, setBuyPriceModified] = useState(false);
  const [sellPriceModified, setSellPriceModified] = useState(false);

  // Calculate totals
  const buyTotal =
    buyPrice && buyAmount
      ? (Number.parseFloat(buyPrice) * Number.parseFloat(buyAmount)).toFixed(2)
      : "0.00";
  const sellTotal =
    sellPrice && sellAmount
      ? (Number.parseFloat(sellPrice) * Number.parseFloat(sellAmount)).toFixed(
          2,
        )
      : "0.00";

  // Function to update URL with token
  const updateUrlWithToken = (token: string) => {
    if (!token) return;
    const url = new URL(window.location.href);
    url.searchParams.set("token", token);
    window.history.pushState({}, "", url);
  };

  // Show notification
  const showNotification = (message: string, type = "success") => {
    setNotification({ show: true, message, type });

    // Auto hide after 5 seconds
    setTimeout(() => {
      setNotification({ show: false, message: "", type: "success" });
    }, 5000);
  };

  // Fetch exchange rate for current token
  const fetchExchangeRate = useCallback(
    async (token: string) => {
      if (!token) return;

      try {
        // Use lowercase for API request as standardized in backend
        const tokenLower = token.toLowerCase();
        const response = await axios.get(
          `/api/v1/market/exchangerate?tokens=${tokenLower}`,
        );

        // Check if response contains rates for the token (in lowercase)
        if (
          response.data &&
          response.data.rates &&
          response.data.rates[tokenLower] !== undefined
        ) {
          const rate = response.data.rates[tokenLower];
          setCurrentPrice(rate);

          // Update buy/sell prices with latest rate
          const formattedRate = rate.toFixed(2);

          // Only update input fields if user hasn't modified them
          if (!buyPriceModified) {
            setBuyPrice(formattedRate);
          }

          if (!sellPriceModified) {
            setSellPrice(formattedRate);
          }

          // Update market order calculations if needed
          if (orderType === "market") {
            if (buyUsdtAmount) {
              const tokenAmount = Number.parseFloat(buyUsdtAmount) / rate;
              setBuyAmount(tokenAmount.toFixed(6));
            }

            if (sellAmount) {
              const usdtAmount = Number.parseFloat(sellAmount) * rate;
              setSellUsdtAmount(usdtAmount.toFixed(2));
            }
          }
        }
      } catch (error) {
        console.error("Failed to fetch exchange rate:", error);
      }
    },
    [orderType, buyUsdtAmount, sellAmount, buyPriceModified, sellPriceModified],
  );

  // Fetch available tokens
  const fetchAvailableTokens = useCallback(async () => {
    try {
      const response = await axios.get("/api/v1/crypto/token");
      const tokens = response.data.filter(
        (token: { tokenId: string }) => token.tokenId.toLowerCase() !== "usdt",
      );
      setAvailableTokens(tokens);

      // Check URL for token parameter
      const params = new URLSearchParams(window.location.search);
      const tokenParam = params.get("token");

      if (tokenParam && tokens.length > 0) {
        // If token parameter exists in URL
        const token = tokenParam.toLowerCase();
        const matchingToken = tokens.find(
          (t: { tokenId: string }) => t.tokenId.toLowerCase() === token,
        );

        if (matchingToken) {
          setCurrentToken(token);
          setSelectedPair(`${matchingToken.tokenId.toUpperCase()}/USDT`);
          fetchExchangeRate(token);
          return;
        }
      }

      // Set default token if none in URL and none selected yet
      if (!currentToken && tokens.length > 0) {
        const defaultToken = tokens[0].tokenId.toLowerCase();
        setCurrentToken(defaultToken);
        setSelectedPair(`${tokens[0].tokenId.toUpperCase()}/USDT`);
        updateUrlWithToken(defaultToken);
        fetchExchangeRate(defaultToken);
      }
    } catch (error) {
      console.error("Failed to fetch tokens:", error);
    }
  }, [currentToken, fetchExchangeRate]);

  // Fetch order book data
  const fetchOrderBook = useCallback(async () => {
    if (!currentToken) return;

    try {
      const response = await axios.get(
        `/api/v1/orderview/sortedorders?token=${currentToken.toLowerCase()}`,
      );
      setOrderBook({
        asks: response.data.sell || [],
        bids: response.data.buy || [],
      });
    } catch (error) {
      console.error("Failed to fetch order book:", error);
    }
  }, [currentToken]);

  // Fetch recent trades
  const fetchRecentTrades = useCallback(
    async (tokenToFetch = null) => {
      const token = tokenToFetch || currentToken;
      if (!token) return;

      try {
        const response = await axios.get(
          `/api/v1/orderview/recentorders?token=${token.toLowerCase()}`,
        );

        // Filter for current token
        const filteredTrades = response.data.orders.filter(
          (order: { fromTokenId: string; toTokenId: string }) =>
            (order.fromTokenId.toLowerCase() === token.toLowerCase() &&
              order.toTokenId.toLowerCase() === "usdt") ||
            (order.fromTokenId.toLowerCase() === "usdt" &&
              order.toTokenId.toLowerCase() === token.toLowerCase()),
        );

        // Format trades data
        const formattedTrades = filteredTrades.map(
          (order: {
            limitPrice: number;
            fromTokenId: string;
            toAmount: number;
            fromAmount: number;
            creation: string | number | Date;
          }) => ({
            price: order.limitPrice,
            amount:
              order.fromTokenId.toLowerCase() === "usdt"
                ? order.toAmount || order.fromAmount / order.limitPrice
                : order.fromAmount || order.toAmount / order.limitPrice,
            time: new Date(order.creation).toLocaleTimeString(),
            type: order.fromTokenId.toLowerCase() === "usdt" ? "buy" : "sell",
          }),
        );

        // Limit to 12 trades as requested
        setRecentTrades(formattedTrades.slice(0, 12));
      } catch (error) {
        console.error("Failed to fetch recent trades:", error);
      }
    },
    [currentToken],
  );

  // Fetch balances
  const fetchBalances = useCallback(async () => {
    if (!userId || !currentToken) return;

    try {
      // Fetch USDT balance
      const usdtResponse = await axios.get(
        `/api/v1/crypto/holdings/${userId}/usdt`,
      );
      setUsdtBalance({
        available: usdtResponse.data.availableBalance,
        actual: usdtResponse.data.actualBalance,
      });

      // Fetch selected token balance if not USDT
      if (currentToken !== "usdt") {
        const tokenResponse = await axios.get(
          `/api/v1/crypto/holdings/${userId}/${currentToken}`,
        );
        setTokenBalance({
          available: tokenResponse.data.availableBalance,
          actual: tokenResponse.data.actualBalance,
        });
      }
    } catch (error) {
      console.error("Failed to fetch balances:", error);
      // Set default values if balance not found
      if (error.response && error.response.status === 404) {
        if (currentToken !== "usdt") {
          setTokenBalance({ available: 0, actual: 0 });
        }
      }
    }
  }, [userId, currentToken]);

  // Fetch transactions for current pair
  const fetchTransactions = useCallback(
    async (isInitialLoad = false) => {
      if (!userId || !currentToken) return;

      // Only show loading indicator on initial load or token change
      if (isInitialLoad) {
        setLoadingTransactions(true);
      }

      try {
        const response = await axios.get(
          `/api/v1/transaction/crypto/user/${userId}`,
        );

        // Filter transactions for the current trading pair
        const filteredTransactions = response.data.filter(
          (tx: { fromTokenId: string; toTokenId: string }) =>
            (tx.fromTokenId.toLowerCase() === currentToken.toLowerCase() &&
              tx.toTokenId.toLowerCase() === "usdt") ||
            (tx.fromTokenId.toLowerCase() === "usdt" &&
              tx.toTokenId.toLowerCase() === currentToken.toLowerCase()),
        );

        // Sort transactions by creation date (newest first)
        const sortedTransactions = filteredTransactions.sort(
          (
            a: { creation: string | number | Date },
            b: { creation: string | number | Date },
          ) => new Date(b.creation).getTime() - new Date(a.creation).getTime(),
        );

        setTransactions(sortedTransactions);
      } catch (error) {
        console.error("Failed to fetch transactions:", error);
      } finally {
        if (isInitialLoad) {
          setLoadingTransactions(false);
        }
      }
    },
    [userId, currentToken],
  );

  // Fetch all transactions
  const fetchAllTransactions = useCallback(
    async (isInitialLoad = false) => {
      if (!userId) return;

      // Only show loading indicator on initial load
      if (isInitialLoad) {
        setLoadingAllTransactions(true);
      }

      try {
        const response = await axios.get(
          `/api/v1/transaction/crypto/user/${userId}`,
        );

        // Sort transactions by creation date (newest first)
        const sortedTransactions = response.data.sort(
          (
            a: { creation: string | number | Date },
            b: { creation: string | number | Date },
          ) => new Date(b.creation).getTime() - new Date(a.creation).getTime(),
        );

        setAllTransactions(sortedTransactions);
      } catch (error) {
        console.error("Failed to fetch all transactions:", error);
      } finally {
        if (isInitialLoad) {
          setLoadingAllTransactions(false);
        }
      }
    },
    [userId],
  );

  // Handle pair change
  const handlePairChange = (newPair: React.SetStateAction<string>) => {
    const [token] = (typeof newPair === "string" ? newPair : "").split("/");
    setSelectedPair(newPair);
    const newToken = token.toLowerCase();
    setCurrentToken(newToken);
    updateUrlWithToken(newToken); // Update URL

    // Reset form values
    setBuyAmount("");
    setBuyUsdtAmount("");
    setSellAmount("");
    setSellUsdtAmount("");

    // Reset price modification flags to get fresh prices for new token
    setBuyPriceModified(false);
    setSellPriceModified(false);

    // Set loading true for transaction display when changing token
    setLoadingTransactions(true);
  };

  // Handle buy price change
  const handleBuyPriceChange = (e: { target: { value: unknown } }) => {
    const newPrice = e.target.value as string;
    setBuyPrice(newPrice);
    setBuyPriceModified(true); // Flag that user has modified this value

    // If USDT amount is set, recalculate token amount
    if (buyUsdtAmount) {
      const tokenAmount =
        Number.parseFloat(buyUsdtAmount) / Number.parseFloat(newPrice || "1");
      setBuyAmount(tokenAmount.toFixed(6));
    }
  };

  // Handle buy USDT amount change
  const handleBuyUsdtAmountChange = (e: { target: { value: unknown } }) => {
    const newUsdtAmount = e.target.value as string;
    setBuyUsdtAmount(newUsdtAmount);

    // Calculate token amount based on USDT and price
    if (newUsdtAmount) {
      const price =
        orderType === "market"
          ? currentPrice
          : Number.parseFloat(buyPrice || "1");
      const tokenAmount = Number.parseFloat(newUsdtAmount as string) / price;
      setBuyAmount(tokenAmount.toFixed(6));
    } else {
      setBuyAmount("");
    }
  };

  // Handle buy amount change
  const handleBuyAmountChange = (e: { target: { value: unknown } }) => {
    const newAmount = e.target.value as string;
    setBuyAmount(newAmount);

    // Calculate USDT amount based on token amount and price
    if (newAmount) {
      const price =
        orderType === "market"
          ? currentPrice
          : Number.parseFloat(buyPrice || "1");
      const usdtAmount = Number.parseFloat(newAmount) * price;
      setBuyUsdtAmount(usdtAmount.toFixed(2));
    } else {
      setBuyUsdtAmount("");
    }
  };

  // Handle sell price change
  const handleSellPriceChange = (e: { target: { value: unknown } }) => {
    const newPrice = e.target.value as string;
    setSellPrice(newPrice);
    setSellPriceModified(true); // Flag that user has modified this value

    // If token amount is set, recalculate USDT amount
    if (sellAmount) {
      const usdtAmount =
        Number.parseFloat(sellAmount) * Number.parseFloat(newPrice || "1");
      setSellUsdtAmount(usdtAmount.toFixed(2));
    }
  };

  // Handle sell amount change
  const handleSellAmountChange = (e: { target: { value: unknown } }) => {
    const newAmount = e.target.value as string;
    setSellAmount(newAmount);

    // Calculate USDT amount based on token amount and price
    if (newAmount) {
      const price =
        orderType === "market"
          ? currentPrice
          : Number.parseFloat(sellPrice || "1");
      const usdtAmount = Number.parseFloat(newAmount) * price;
      setSellUsdtAmount(usdtAmount.toFixed(2));
    } else {
      setSellUsdtAmount("");
    }
  };

  // Handle sell USDT amount change
  const handleSellUsdtAmountChange = (e: { target: { value: unknown } }) => {
    const newUsdtAmount = e.target.value;
    setSellUsdtAmount(newUsdtAmount as string);

    // Calculate token amount based on USDT and price
    if (newUsdtAmount) {
      const price =
        orderType === "market"
          ? currentPrice
          : Number.parseFloat(sellPrice || "1");
      const tokenAmount = Number.parseFloat(newUsdtAmount as string) / price;
      setSellAmount(tokenAmount.toFixed(6));
    } else {
      setSellAmount("");
    }
  };

  // Place buy order
  const handleBuySubmit = async (e: { preventDefault: () => void }) => {
    e.preventDefault();

    if (!userId || !buyAmount || Number.parseFloat(buyAmount) <= 0) {
      return;
    }

    setIsProcessing(true);

    const tokenAmount = Number.parseFloat(buyAmount);
    const price =
      orderType === "market" ? currentPrice : Number.parseFloat(buyPrice);

    // Always calculate the orderCost as price * tokenAmount
    const usdtAmount = price * tokenAmount;

    const orderData = {
      userId: userId,
      orderType: orderType, // "limit" or "market"
      side: "buy", // Buy side
      baseTokenId: currentToken, // Selected token (crypto)
      quoteTokenId: "usdt", // Quote token is always USDT
      limitPrice: price, // Price per token
      quantity: tokenAmount, // Amount of tokens to buy
      orderCost: usdtAmount, // Total USDT amount to spend
    };

    try {
      await axios.post("/api/v1/order/create_order", orderData);

      // Show success notification - different for market vs limit orders
      if (orderType === "market") {
        showNotification(
          `Buy order placed successfully: ${buyAmount} ${currentToken.toUpperCase()}`,
        );
      } else {
        showNotification(
          `Buy order placed successfully: ${buyAmount} ${currentToken.toUpperCase()} at $${price.toFixed(2)}`,
        );
      }

      setBuyAmount("");
      setBuyUsdtAmount("");

      // Refresh data
      fetchBalances();
      fetchOrderBook();
      fetchRecentTrades();
      // Set loading for transactions after placing order
      setLoadingTransactions(true);
      fetchTransactions(true);
      fetchAllTransactions();
    } catch (error) {
      console.error("Buy order failed:", error);
      showNotification(
        `Buy order failed: ${error.response?.data?.error || "Unknown error"}`,
        "error",
      );
    } finally {
      setIsProcessing(false);
      setBuyPriceModified(false);
      setSellPriceModified(false);
    }
  };

  // Place sell order
  const handleSellSubmit = async (e: { preventDefault: () => void }) => {
    e.preventDefault();

    if (!userId || !sellAmount || Number.parseFloat(sellAmount) <= 0) {
      return;
    }

    setIsProcessing(true);

    const tokenAmount = Number.parseFloat(sellAmount);
    const price =
      orderType === "market" ? currentPrice : Number.parseFloat(sellPrice);

    // Always calculate the orderCost as price * tokenAmount
    const usdtAmount = price * tokenAmount;

    const orderData = {
      userId: userId,
      orderType: orderType, // "limit" or "market"
      side: "sell", // Sell side
      baseTokenId: currentToken, // Selected token (crypto)
      quoteTokenId: "usdt", // Quote token is always USDT
      limitPrice: price, // Price per token
      quantity: tokenAmount, // Amount of tokens to sell
      orderCost: usdtAmount, // Total USDT amount to receive
    };

    try {
      await axios.post("/api/v1/order/create_order", orderData);

      // Show success notification - different for market vs limit orders
      if (orderType === "market") {
        showNotification(
          `Sell order placed successfully: ${sellAmount} ${currentToken.toUpperCase()}`,
        );
      } else {
        showNotification(
          `Sell order placed successfully: ${sellAmount} ${currentToken.toUpperCase()} at $${price.toFixed(2)}`,
        );
      }

      setSellAmount("");
      setSellUsdtAmount("");

      // Refresh data
      fetchBalances();
      fetchOrderBook();
      fetchRecentTrades();
      // Set loading for transactions after placing order
      setLoadingTransactions(true);
      fetchTransactions(true);
      fetchAllTransactions();
    } catch (error) {
      console.error("Sell order failed:", error);
      showNotification(
        `Sell order failed: ${error.response?.data?.error || "Unknown error"}`,
        "error",
      );
    } finally {
      setIsProcessing(false);
      setBuyPriceModified(false);
      setSellPriceModified(false);
    }
  };

  // Reset form values when order type changes
  useEffect(() => {
    if (orderType === "market") {
      // Reset flags when switching to market orders
      setBuyPriceModified(false);
      setSellPriceModified(false);

      // For market orders, use current price from BTC/USDT card
      if (buyUsdtAmount) {
        const tokenAmount = Number.parseFloat(buyUsdtAmount) / currentPrice;
        setBuyAmount(tokenAmount.toFixed(6));
      }

      if (sellAmount) {
        const usdtAmount = Number.parseFloat(sellAmount) * currentPrice;
        setSellUsdtAmount(usdtAmount.toFixed(2));
      }
    }
  }, [orderType, currentPrice, buyUsdtAmount, sellAmount]);

  // Initialize data
  useEffect(() => {
    fetchAvailableTokens();
    fetchAllTransactions(true);
    setInitialLoad(true);
  }, [fetchAvailableTokens, fetchAllTransactions]);

  // Update data when token changes
  useEffect(() => {
    if (currentToken) {
      fetchOrderBook();
      fetchRecentTrades();
      fetchBalances();
      fetchTransactions(initialLoad);
      if (initialLoad) {
        setInitialLoad(false);
      }
    }
  }, [
    currentToken,
    fetchOrderBook,
    fetchRecentTrades,
    fetchBalances,
    fetchTransactions,
    initialLoad,
  ]);

  // Periodic data refresh
  useEffect(() => {
    if (!currentToken) return;

    const refreshAllData = () => {
      fetchOrderBook();
      fetchRecentTrades();
      fetchExchangeRate(currentToken);
      fetchBalances();
      // Pass false to avoid showing loading state during auto-refresh
      fetchTransactions(false);
      fetchAllTransactions(false);
    };

    // Set up interval
    const interval = setInterval(refreshAllData, 10000);

    return () => clearInterval(interval);
  }, [
    currentToken,
    fetchOrderBook,
    fetchRecentTrades,
    fetchExchangeRate,
    fetchBalances,
    fetchTransactions,
    fetchAllTransactions,
  ]);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Notification popup */}
      {notification.show && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-md p-4 rounded-lg shadow-lg ${
            notification.type === "success"
              ? "bg-green-100 border border-green-400"
              : "bg-red-100 border border-red-400"
          }`}
        >
          <div className="flex items-start justify-between">
            <div
              className={`text-sm font-medium ${
                notification.type === "success"
                  ? "text-green-800"
                  : "text-red-800"
              }`}
            >
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
                <CardDescription>
                  {currentToken
                    ? `${currentToken.toUpperCase()} to Tether`
                    : "Loading..."}
                </CardDescription>
              </div>
              <Select value={selectedPair} onValueChange={handlePairChange}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Select pair" />
                </SelectTrigger>
                <SelectContent>
                  {availableTokens.map((token) => (
                    <SelectItem
                      key={token.tokenId}
                      value={`${token.tokenId.toUpperCase()}/USDT`}
                    >
                      {token.tokenId.toUpperCase()}/USDT
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {currentPrice > 0
                ? `$${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                : "Loading..."}
            </div>
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
                    <div className="text-right">
                      Amount{" "}
                      {currentToken ? `(${currentToken.toUpperCase()})` : ""}
                    </div>
                    <div className="text-right">Total (USDT)</div>
                  </div>
                  <div className="space-y-1">
                    {orderBook.asks.length > 0 ? (
                      orderBook.asks.map((ask, index) => (
                        <div
                          key={index}
                          className="grid grid-cols-3 text-xs text-red-500"
                        >
                          <div>{ask.limitPrice?.toFixed(2) || 0}</div>
                          <div className="text-right">
                            {ask.fromAmount?.toFixed(6) || 0}
                          </div>
                          <div className="text-right">
                            {(ask.limitPrice * ask.fromAmount)?.toFixed(2) || 0}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-xs text-muted-foreground py-2">
                        No sell orders
                      </div>
                    )}
                  </div>
                </div>

                <div className="py-2 text-center font-bold text-lg">
                  {currentPrice > 0
                    ? `$${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : "Loading..."}
                </div>

                <div>
                  <div className="space-y-1">
                    {orderBook.bids.length > 0 ? (
                      orderBook.bids.map((bid, index) => (
                        <div
                          key={index}
                          className="grid grid-cols-3 text-xs text-green-500"
                        >
                          <div>{bid.limitPrice?.toFixed(2) || 0}</div>
                          <div className="text-right">
                            {bid.toAmount?.toFixed(6) ||
                              (bid.fromAmount / bid.limitPrice)?.toFixed(6) ||
                              0}
                          </div>
                          <div className="text-right">
                            {bid.fromAmount?.toFixed(2) || 0}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-xs text-muted-foreground py-2">
                        No buy orders
                      </div>
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
                  <div className="text-right">
                    Amount{" "}
                    {currentToken ? `(${currentToken.toUpperCase()})` : ""}
                  </div>
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
                        <div className="text-right">
                          {trade.amount.toFixed(6)}
                        </div>
                        <div className="text-right">
                          {(trade.price * trade.amount).toFixed(2)}
                        </div>
                        <div className="text-right">{trade.time}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-xs text-muted-foreground py-2">
                      No recent trades
                    </div>
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
                <TabsTrigger value="all-transactions">
                  All Transactions
                </TabsTrigger>
              </TabsList>

              <TabsContent value="current-pair">
                {loadingTransactions ? (
                  <div className="flex justify-center py-4">
                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : transactions.length > 0 ? (
                  <div className="space-y-4 max-h-120 overflow-y-auto">
                    {transactions.map((tx) => (
                      <div
                        key={tx.transactionId}
                        className="border rounded-md p-4"
                      >
                        <div className="flex justify-between items-center mb-3">
                          <div className="text-base font-medium">
                            {tx.fromTokenId.toLowerCase() === "usdt"
                              ? "Buy"
                              : "Sell"}{" "}
                            {tx.fromTokenId.toLowerCase() === "usdt"
                              ? tx.toTokenId.toUpperCase()
                              : tx.fromTokenId.toUpperCase()}
                            <span className="ml-2 text-sm text-muted-foreground">
                              {tx.orderType || "limit"} order
                            </span>
                          </div>
                          <div
                            className={`text-sm px-3 py-1 rounded-full ${
                              tx.status === "completed"
                                ? "bg-green-100 text-green-800"
                                : tx.status === "cancelled"
                                  ? "bg-red-100 text-red-800"
                                  : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            {tx.status}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 text-sm gap-2 mb-2">
                          <div>
                            <div className="text-muted-foreground">
                              Order Amount
                            </div>
                            <div className="font-medium">
                              {tx.fromTokenId.toLowerCase() === "usdt"
                                ? `${tx.toAmount} ${tx.toTokenId.toUpperCase()}`
                                : `${tx.fromAmount} ${tx.fromTokenId.toUpperCase()}`}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">
                              Fulfilled
                            </div>
                            <div className="font-medium">
                              {tx.fromTokenId.toLowerCase() === "usdt"
                                ? `${tx.toAmountActual || tx.toAmount} ${tx.toTokenId.toUpperCase()}`
                                : `${tx.fromAmountActual || tx.fromAmount} ${tx.fromTokenId.toUpperCase()}`}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 text-sm gap-2">
                          <div>
                            <div className="text-muted-foreground">Paid</div>
                            <div className="font-medium">
                              {tx.fromAmountActual || tx.fromAmount}{" "}
                              {tx.fromTokenId.toUpperCase()}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">
                              Received
                            </div>
                            <div className="font-medium">
                              {tx.toAmountActual || tx.toAmount}{" "}
                              {tx.toTokenId.toUpperCase()}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 text-sm gap-2 mt-2">
                          <div>
                            <div className="text-muted-foreground">
                              Limit Price
                            </div>
                            <div className="font-medium">
                              ${tx.limitPrice.toFixed(2)}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">
                              Total Value
                            </div>
                            <div className="font-medium">
                              $
                              {(tx.fromTokenId.toLowerCase() === "usdt"
                                ? tx.fromAmount
                                : tx.toAmount
                              ).toFixed(2)}
                            </div>
                          </div>
                        </div>

                        <div className="text-sm text-muted-foreground mt-2">
                          {new Date(tx.creation).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-10 text-muted-foreground text-base">
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
                  <div className="space-y-4 max-h-120 overflow-y-auto">
                    {allTransactions.map((tx) => (
                      <div
                        key={tx.transactionId}
                        className="border rounded-md p-4"
                      >
                        <div className="flex justify-between items-center mb-3">
                          <div className="text-base font-medium">
                            {tx.fromTokenId.toLowerCase() === "usdt"
                              ? "Buy"
                              : "Sell"}{" "}
                            {tx.fromTokenId.toLowerCase() === "usdt"
                              ? tx.toTokenId.toUpperCase()
                              : tx.fromTokenId.toUpperCase()}
                            <span className="ml-2 text-sm text-muted-foreground">
                              {tx.orderType || "limit"} order
                            </span>
                          </div>
                          <div
                            className={`text-sm px-3 py-1 rounded-full ${
                              tx.status === "completed"
                                ? "bg-green-100 text-green-800"
                                : tx.status === "cancelled"
                                  ? "bg-red-100 text-red-800"
                                  : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            {tx.status}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 text-sm gap-2 mb-2">
                          <div>
                            <div className="text-muted-foreground">
                              Order Amount
                            </div>
                            <div className="font-medium">
                              {tx.fromTokenId.toLowerCase() === "usdt"
                                ? `${tx.toAmount} ${tx.toTokenId.toUpperCase()}`
                                : `${tx.fromAmount} ${tx.fromTokenId.toUpperCase()}`}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">
                              Fulfilled
                            </div>
                            <div className="font-medium">
                              {tx.fromTokenId.toLowerCase() === "usdt"
                                ? `${tx.toAmountActual || tx.toAmount} ${tx.toTokenId.toUpperCase()}`
                                : `${tx.fromAmountActual || tx.fromAmount} ${tx.fromTokenId.toUpperCase()}`}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 text-sm gap-2">
                          <div>
                            <div className="text-muted-foreground">Paid</div>
                            <div className="font-medium">
                              {tx.fromAmountActual || tx.fromAmount}{" "}
                              {tx.fromTokenId.toUpperCase()}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">
                              Received
                            </div>
                            <div className="font-medium">
                              {tx.toAmountActual || tx.toAmount}{" "}
                              {tx.toTokenId.toUpperCase()}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 text-sm gap-2 mt-2">
                          <div>
                            <div className="text-muted-foreground">
                              Limit Price
                            </div>
                            <div className="font-medium">
                              ${tx.limitPrice.toFixed(2)}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">
                              Total Value
                            </div>
                            <div className="font-medium">
                              $
                              {(tx.fromTokenId.toLowerCase() === "usdt"
                                ? tx.fromAmount
                                : tx.toAmount
                              ).toFixed(2)}
                            </div>
                          </div>
                        </div>

                        <div className="text-sm text-muted-foreground mt-2">
                          {new Date(tx.creation).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-10 text-muted-foreground text-base">
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
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="buy">Buy</TabsTrigger>
                <TabsTrigger value="sell">Sell</TabsTrigger>
              </TabsList>

              <TabsContent value="buy" className="space-y-4 pt-4">
                <form onSubmit={handleBuySubmit}>
                  <div className="space-y-4">
                    {orderType === "limit" && (
                      <div className="space-y-2">
                        <Label htmlFor="buy-price">
                          Price per{" "}
                          {currentToken ? currentToken.toUpperCase() : ""}{" "}
                          (USDT)
                        </Label>
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
                      <Label htmlFor="buy-usdt-amount">
                        USDT Amount to Spend
                      </Label>
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
                      <Label htmlFor="buy-amount">
                        Amount of{" "}
                        {currentToken ? currentToken.toUpperCase() : ""} to Buy
                      </Label>
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
                        <div className="font-medium">
                          {buyUsdtAmount || buyTotal} USDT
                        </div>
                      </div>

                      <div className="text-xs text-right">
                        <div className="flex items-center justify-end">
                          <span className="text-muted-foreground">
                            Total Balance
                          </span>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="ml-1 inline-flex items-center justify-center text-muted-foreground"
                                >
                                  <Info className="h-3 w-3" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="w-[200px] text-xs">
                                  Total Balance is your full balance. Available
                                  Balance is what you can use for trading (after
                                  pending orders).
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                        <div>{usdtBalance.actual.toFixed(2)} USDT</div>
                        <div className="text-muted-foreground mt-1">
                          Available Balance
                        </div>
                        <div>{usdtBalance.available.toFixed(2)} USDT</div>
                      </div>
                    </div>

                    <Button
                      type="submit"
                      className="w-full bg-green-600 hover:bg-green-700"
                      disabled={
                        isProcessing ||
                        !buyAmount ||
                        Number.parseFloat(buyAmount) <= 0 ||
                        Number.parseFloat(buyUsdtAmount || buyTotal) >
                          usdtBalance.available
                      }
                    >
                      {isProcessing ? (
                        <div className="flex items-center">
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />{" "}
                          Processing...
                        </div>
                      ) : (
                        `Buy ${currentToken ? currentToken.toUpperCase() : ""}`
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
                        <Label htmlFor="sell-price">
                          Price per{" "}
                          {currentToken ? currentToken.toUpperCase() : ""}{" "}
                          (USDT)
                        </Label>
                        <Input
                          id="sell-price"
                          type="number"
                          step="0.01"
                          value={sellPrice}
                          onChange={handleSellPriceChange}
                          required
                        />
                      </div>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="sell-amount">
                        Amount of{" "}
                        {currentToken ? currentToken.toUpperCase() : ""} to Sell
                      </Label>
                      <Input
                        id="sell-amount"
                        type="number"
                        step="0.0001"
                        placeholder="0.00"
                        value={sellAmount}
                        onChange={handleSellAmountChange}
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="sell-usdt-amount">
                        USDT Amount to Receive
                      </Label>
                      <Input
                        id="sell-usdt-amount"
                        type="number"
                        step="0.01"
                        placeholder="0.00"
                        value={sellUsdtAmount}
                        onChange={handleSellUsdtAmountChange}
                      />
                    </div>

                    <Separator />

                    <div className="flex justify-between items-center">
                      <div className="text-sm">
                        <div className="text-muted-foreground">Total Order</div>
                        <div className="font-medium">
                          {sellUsdtAmount || sellTotal} USDT
                        </div>
                      </div>

                      <div className="text-xs text-right">
                        <div className="flex items-center justify-end">
                          <span className="text-muted-foreground">
                            Total Balance
                          </span>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="ml-1 inline-flex items-center justify-center text-muted-foreground"
                                >
                                  <Info className="h-3 w-3" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="w-[200px] text-xs">
                                  Total Balance is your full balance. Available
                                  Balance is what you can use for trading (after
                                  pending orders).
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                        <div>
                          {tokenBalance.actual.toFixed(6)}{" "}
                          {currentToken ? currentToken.toUpperCase() : ""}
                        </div>
                        <div className="text-muted-foreground mt-1">
                          Available Balance
                        </div>
                        <div>
                          {tokenBalance.available.toFixed(6)}{" "}
                          {currentToken ? currentToken.toUpperCase() : ""}
                        </div>
                      </div>
                    </div>

                    <Button
                      type="submit"
                      className="w-full bg-red-600 hover:bg-red-700"
                      disabled={
                        isProcessing ||
                        !sellAmount ||
                        Number.parseFloat(sellAmount) <= 0 ||
                        Number.parseFloat(sellAmount) > tokenBalance.available
                      }
                    >
                      {isProcessing ? (
                        <div className="flex items-center">
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />{" "}
                          Processing...
                        </div>
                      ) : (
                        `Sell ${currentToken ? currentToken.toUpperCase() : ""}`
                      )}
                    </Button>
                  </div>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
