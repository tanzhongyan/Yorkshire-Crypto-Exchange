"use client";

import { useEffect, useState, useCallback } from "react";
import { ArrowDown, RefreshCw } from "lucide-react";
import { getCookie } from "@/lib/cookies";
import axios from "@/lib/axios";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

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

export default function RampPage() {
  const [fromAmount, setFromAmount] = useState("");
  const [toAmount, setToAmount] = useState("");
  const [fromCurrency, setFromCurrency] = useState("sgd"); // Default from currency
  const [toCurrency, setToCurrency] = useState("usdt"); // Default to currency
  const [direction, setDirection] = useState("fiattocrypto"); // Default direction
  const [isProcessing, setIsProcessing] = useState(false);
  const [exchangeRates, setExchangeRates] = useState({});
  const [fiatAccounts, setFiatAccounts] = useState([]);
  const [cryptoHoldings, setCryptoHoldings] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [availableFiatCurrencies, setAvailableFiatCurrencies] = useState([]);

  // Get user ID from cookie
  const userId = getCookie("userId");

  // Fetch all exchange rates once (USD based)
  const fetchAllExchangeRates = useCallback(async () => {
    try {
      // Use axios to call our API endpoint instead of direct fetch with API key
      const response = await axios.get('/api/v1/market/fiatrates');
      
      if (response.status === 200 && response.data) {
        // Add USD to USD rate (1.0) if not already present
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

  // Update to amount when from amount changes
  const updateToAmount = useCallback((newFromAmount, fromCurr, toCurr) => {
    const numValue = parseFloat(newFromAmount) || 0;
    
    if (newFromAmount && !isNaN(numValue) && Object.keys(exchangeRates).length > 0) {
      // For USDT, we treat it as USD for conversion purposes
      const fromUpper = fromCurr.toUpperCase();
      const toUpper = toCurr.toUpperCase() === 'USDT' ? 'USD' : toCurr.toUpperCase();
      
      // First convert to USD (which is the base currency for our rates)
      let fromToUsd;
      if (fromUpper === 'USDT' || fromUpper === 'USD') {
        fromToUsd = numValue;
      } else {
        // Convert from source currency to USD
        fromToUsd = numValue / exchangeRates[fromUpper];
      }
      
      // Then convert from USD to target currency
      let result;
      if (toUpper === 'USD' || toUpper === 'USDT') {
        result = fromToUsd;
      } else {
        // Convert from USD to target currency
        result = fromToUsd * exchangeRates[toUpper];
      }
      
      setToAmount(result.toFixed(2));
    } else {
      setToAmount("");
    }
  }, [exchangeRates]);

  // Handle from amount change
  const handleFromAmountChange = (value) => {
    setFromAmount(value);
    updateToAmount(value, fromCurrency, toCurrency);
  };

  // Handle using max available balance
  const handleUseMaxBalance = () => {
    const maxBalance = getAvailableBalance();
    const formattedBalance = maxBalance.toString();
    setFromAmount(formattedBalance);
    updateToAmount(formattedBalance, fromCurrency, toCurrency);
  };

  // Handle swap direction
  const handleSwapPositions = () => {
    // Store current values before swapping
    const oldFromCurrency = fromCurrency;
    const oldToCurrency = toCurrency;
    const oldFromAmount = fromAmount;
    const oldToAmount = toAmount;
    
    // Define new direction
    const newDirection = direction === "fiattocrypto" ? "cryptotofiat" : "fiattocrypto";
    
    // First update the direction
    setDirection(newDirection);
    
    // Use function to update state to ensure consistent rendering
    function updateStates() {
      // Swap currencies
      setFromCurrency(oldToCurrency);
      setToCurrency(oldFromCurrency);
      
      // Swap amounts if they exist
      if (oldToAmount) {
        setFromAmount(oldToAmount);
        
        // Calculate new to amount directly
        const numValue = parseFloat(oldToAmount) || 0;
        if (oldToAmount && !isNaN(numValue) && Object.keys(exchangeRates).length > 0) {
          const fromUpper = oldToCurrency.toUpperCase();
          const toUpper = oldFromCurrency.toUpperCase() === 'USDT' ? 'USD' : oldFromCurrency.toUpperCase();
          
          // Convert to USD
          let fromToUsd;
          if (fromUpper === 'USDT' || fromUpper === 'USD') {
            fromToUsd = numValue;
          } else {
            fromToUsd = numValue / exchangeRates[fromUpper];
          }
          
          // Convert from USD
          let result;
          if (toUpper === 'USD' || toUpper === 'USDT') {
            result = fromToUsd;
          } else {
            result = fromToUsd * exchangeRates[toUpper];
          }
          
          setToAmount(result.toFixed(2));
        } else {
          setToAmount("");
        }
      } else {
        setToAmount("");
      }
    }
    
    // Use requestAnimationFrame to ensure UI updates properly
    requestAnimationFrame(updateStates);
  };

  // Get currency symbol
  const getCurrencySymbol = (code) => {
    if (code.toLowerCase() === "usdt") return "$";
    const currency = FIAT_CURRENCIES.find(c => c.currencyCode.toLowerCase() === code.toLowerCase());
    return currency?.symbol || "$";
  };

  // Handle from currency change
  const handleFromCurrencyChange = (value) => {
    setFromCurrency(value);
    updateToAmount(fromAmount, value, toCurrency);
  };

  // Handle to currency change
  const handleToCurrencyChange = (value) => {
    setToCurrency(value);
    updateToAmount(fromAmount, fromCurrency, value);
  };

  // Calculate available balance based on current from currency
  const getAvailableBalance = () => {
    if (direction === "fiattocrypto") {
      // For fiat to crypto transactions, check fiat account balance
      const account = fiatAccounts.find(acc => acc.currencyCode.toLowerCase() === fromCurrency.toLowerCase());
      return account ? account.balance : 0;
    } else {
      // For crypto to fiat transactions, check USDT available balance
      const holding = cryptoHoldings.find(h => h.tokenId.toLowerCase() === fromCurrency.toLowerCase());
      return holding ? holding.availableBalance : 0;
    }
  };

  // Submit swap
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!fromAmount || Number.parseFloat(fromAmount) <= 0 || !userId) {
      return;
    }

    setIsProcessing(true);

    try {
      // Updated to use camelCase property names in the request payload
      const response = await axios.post("/api/v1/ramp/swap", {
        userId: userId,
        amount: parseFloat(fromAmount),
        fiatCurrency: direction === "fiattocrypto" ? fromCurrency : toCurrency,
        tokenId: direction === "fiattocrypto" ? toCurrency : fromCurrency,
        direction: direction
      });

      // Refresh balances and transactions after successful swap
      fetchFiatAccounts();
      fetchCryptoHoldings();
      fetchTransactions();
      
      // Reset the form
      setFromAmount("");
      setToAmount("");
      
    } catch (error) {
      console.error("Swap failed:", error);
      alert(`Swap failed: ${error.response?.data?.message || "Unknown error"}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Fetch fiat accounts
  const fetchFiatAccounts = useCallback(async () => {
    if (!userId) return;
    
    try {
      const response = await axios.get(`/api/v1/fiat/account/${userId}`);
      setFiatAccounts(response.data);
      
      // Set available fiat currencies
      const currencies = response.data.map((acc) => acc.currencyCode.toLowerCase());
      setAvailableFiatCurrencies(currencies);
      
      // If the user doesn't have SGD, set default to the first available currency
      if (currencies.length > 0 && !currencies.includes("sgd")) {
        setFromCurrency(currencies[0]);
      }
      
    } catch (error) {
      console.error("Failed to load fiat accounts:", error);
    }
  }, [userId]);

  // Fetch crypto holdings - specifically USDT only
  const fetchCryptoHoldings = useCallback(async () => {
    if (!userId) return;
    
    try {
      // Get user's USDT holdings only
      const holdingResponse = await axios.get(`/api/v1/crypto/holdings/${userId}/usdt`);
      setCryptoHoldings([holdingResponse.data]);
    } catch (error) {
      console.error("Failed to load crypto holdings:", error);
      // If holding doesn't exist, set empty array
      setCryptoHoldings([]);
    }
  }, [userId]);

  // Fetch transaction history
  const fetchTransactions = useCallback(async () => {
    if (!userId) return;
    
    try {
      const response = await axios.get(`/api/v1/transaction/fiattocrypto/user/${userId}`);
      const sortedTransactions = response.data.sort(
        (a, b) => new Date(b.creation).getTime() - new Date(a.creation).getTime()
      );
      setTransactions(sortedTransactions);
    } catch (error) {
      console.error("Failed to load transactions:", error);
    } finally {
      setDataLoading(false);
    }
  }, [userId]);

  // Load initial data
  useEffect(() => {
    // Fetch exchange rates once at component initialization
    fetchAllExchangeRates();
    
    if (userId) {
      Promise.all([
        fetchFiatAccounts(),
        fetchCryptoHoldings(),
        fetchTransactions()
      ]);
    } else {
      setDataLoading(false);
    }
  }, [userId, fetchFiatAccounts, fetchCryptoHoldings, fetchTransactions, fetchAllExchangeRates]);

  // Get the current exchange rate between two currencies
  const getCurrentExchangeRate = useCallback((from, to) => {
    const fromUpper = from.toUpperCase();
    const toUpper = to.toUpperCase() === 'USDT' ? 'USD' : to.toUpperCase();
    
    if (Object.keys(exchangeRates).length === 0) {
      return null;
    }
    
    if (fromUpper === 'USDT' || fromUpper === 'USD') {
      return exchangeRates[toUpper] || null;
    } else if (toUpper === 'USD' || toUpper === 'USDT') {
      return 1 / exchangeRates[fromUpper] || null;
    } else {
      // Cross rate calculation: from -> USD -> to
      return exchangeRates[toUpper] / exchangeRates[fromUpper] || null;
    }
  }, [exchangeRates]);

  if (dataLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center">
          <p>Loading your account data...</p>
        </div>
      </div>
    );
  }

  // Get the current rate for display
  const currentRate = getCurrentExchangeRate(fromCurrency, toCurrency);

  return (
    <div className="mx-auto w-full px-4 lg:px-12 max-w-screen-xl grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <div>
          <h2 className="text-lg font-semibold mb-2">Ramp Exchange</h2>
          <Card>
            <CardHeader>
              <CardTitle>Currency Swap</CardTitle>
              <CardDescription>
                Swap between fiat and crypto currencies
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-8">
                {/* From */}
                <div className="space-y-2">
                  <Label>From</Label>
                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                        {getCurrencySymbol(fromCurrency)}
                      </span>
                      <Input
                        type="number"
                        placeholder="0.00"
                        className="pl-10 pr-16"
                        value={fromAmount}
                        onChange={(e) => handleFromAmountChange(e.target.value)}
                        min="0"
                        step="0.01"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2 h-6 text-xs px-2 py-0 hover:bg-secondary"
                        onClick={handleUseMaxBalance}
                      >
                        Max
                      </Button>
                    </div>
                    <Select value={fromCurrency} onValueChange={handleFromCurrencyChange}>
                      <SelectTrigger className="w-[120px]">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {direction === "fiattocrypto" 
                          ? availableFiatCurrencies.map(currency => (
                              <SelectItem key={currency} value={currency}>
                                {currency.toUpperCase()}
                              </SelectItem>
                            ))
                          : <SelectItem value="usdt">USDT</SelectItem>
                        }
                      </SelectContent>
                    </Select>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Available: {parseFloat(getAvailableBalance().toFixed(2)).toLocaleString(undefined, { minimumFractionDigits: 2 })} {fromCurrency.toUpperCase()}
                  </p>
                </div>

                {/* Swap Button */}
                <div className="relative flex justify-center">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t" />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="relative bg-background"
                    onClick={handleSwapPositions}
                  >
                    <ArrowDown className="h-4 w-4" />
                  </Button>
                </div>

                {/* To */}
                <div className="space-y-2">
                  <Label>To</Label>
                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                        {getCurrencySymbol(toCurrency)}
                      </span>
                      <Input
                        type="number"
                        placeholder="0.00"
                        className="pl-10"
                        value={toAmount}
                        readOnly
                      />
                    </div>
                    <Select value={toCurrency} onValueChange={handleToCurrencyChange}>
                      <SelectTrigger className="w-[120px]">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {direction === "fiattocrypto" 
                          ? <SelectItem value="usdt">USDT</SelectItem>
                          : availableFiatCurrencies.map(currency => (
                              <SelectItem key={currency} value={currency}>
                                {currency.toUpperCase()}
                              </SelectItem>
                            ))
                        }
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Exchange Rate Details */}
                <div className="rounded-md bg-muted p-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Exchange Rate</span>
                    <span>
                      1 {fromCurrency.toUpperCase()} = {currentRate ? (1 / currentRate).toFixed(6) : "..."} {toCurrency.toUpperCase()}
                    </span>
                  </div>
                  {fromAmount && toAmount && (
                    <div className="mt-2 flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">You will receive</span>
                      <span className="font-medium">
                        {toAmount} {toCurrency.toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isProcessing || !fromAmount || Number.parseFloat(fromAmount) <= 0 || Number.parseFloat(fromAmount) > getAvailableBalance()}
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    "Swap"
                  )}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </div>

        {/* Fiat Accounts */}
        {fiatAccounts.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold mt-6">Your Fiat Accounts</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {fiatAccounts.map((account) => (
                <Card key={account.currencyCode} className="flex flex-col items-center text-center">
                  <CardHeader>
                    <CardTitle>{account.currencyCode.toUpperCase()}</CardTitle>
                    <CardDescription>Balance</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">
                      {FIAT_CURRENCIES.find(c => c.currencyCode.toLowerCase() === account.currencyCode.toLowerCase())?.symbol || '$'}
                      {parseFloat(account.balance.toFixed(2)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* USDT Holdings */}
        <div className="space-y-2">
          <h2 className="text-lg font-semibold mt-6">Your Crypto Wallet</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {cryptoHoldings.length > 0 ? (
              cryptoHoldings.map((holding) => (
                <Card key={holding.tokenId} className="flex flex-col items-center text-center">
                  <CardHeader>
                    <CardTitle>{holding.tokenId.toUpperCase()}</CardTitle>
                    <CardDescription>Balance</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">
                      ${parseFloat(holding.actualBalance.toFixed(2)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Available: ${parseFloat(holding.availableBalance.toFixed(2)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card className="flex flex-col items-center text-center">
                <CardHeader>
                  <CardTitle>USDT</CardTitle>
                  <CardDescription>Balance</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold">
                    $0.00
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Transactions */}
      <div className="space-y-2 overflow-y-auto max-h-[80vh]">
        <h2 className="text-lg font-semibold">Ramp Transactions</h2>
        {transactions.length > 0 ? (
          <div className="space-y-2">
            {transactions.map((txn) => (
              <Card key={txn.transactionId} className="flex flex-col">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-sm">
                      {txn.direction === "fiattocrypto" ? "FIAT → CRYPTO" : "CRYPTO → FIAT"}
                    </CardTitle>
                    <CardDescription>
                      {new Date(txn.creation).toLocaleString()}
                    </CardDescription>
                  </div>
                  <div className={`text-sm font-semibold ${txn.status === 'completed' ? 'text-green-600' : txn.status === 'cancelled' ? 'text-red-600' : 'text-yellow-600'}`}>
                    {txn.status.toUpperCase()}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-muted-foreground">From</p>
                      <p className="font-semibold">
                        {parseFloat(txn.fromAmount.toFixed(2)).toLocaleString(undefined, { minimumFractionDigits: 2 })} {txn.direction === "fiattocrypto" ? txn.currencyCode.toUpperCase() : txn.tokenId.toUpperCase()}
                      </p>
                    </div>
                    <ArrowDown className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">To</p>
                      <p className="font-semibold">
                        {parseFloat(txn.toAmount.toFixed(2)).toLocaleString(undefined, { minimumFractionDigits: 2 })} {txn.direction === "fiattocrypto" ? txn.tokenId.toUpperCase() : txn.currencyCode.toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    <p>Rate: {(txn.toAmount / txn.fromAmount).toFixed(6)}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <p>No swap transactions yet</p>
          </div>
        )}
      </div>
    </div>
  );
}