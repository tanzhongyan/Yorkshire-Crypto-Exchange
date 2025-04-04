"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CreditCard } from "lucide-react";

import { getCookie } from "@/lib/cookies";
import axios from "@/lib/axios";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
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

export default function DepositPage() {
  const [amount, setAmount] = useState("");
  const [currencyCode, setCurrencyCode] = useState("sgd"); // Default to SGD
  const [paymentMethod, setPaymentMethod] = useState("credit-card");
  const [isProcessing, setIsProcessing] = useState(false);
  const [fiatAccounts, setFiatAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [statusMessage, setStatusMessage] = useState<"success" | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [pendingLinks, setPendingLinks] = useState<any>({});
  const [dataLoading, setDataLoading] = useState(true);

  const searchParams = useSearchParams();

  // Get the currency symbol for the selected currency
  const getCurrencySymbol = () => {
    const currency = FIAT_CURRENCIES.find(c => c.currencyCode === currencyCode);
    return currency?.symbol || "$";
  };

  useEffect(() => {
    const fetchFiatAccounts = async () => {
      try {
        const userId = getCookie("userId");
        if (!userId) return;

        const response = await axios.get(`/api/v1/fiat/account/${userId}`);
        setFiatAccounts(response.data);
      } catch (error) {
        console.error("Failed to load fiat accounts", error);
      }
    };

    const fetchTransactions = async () => {
      try {
        const userId = getCookie("userId");
        if (!userId) return;

        const response = await axios.get(`/api/v1/transaction/fiatuser/${userId}`);
        const transactions = response.data.sort(
          (a: any, b: any) => new Date(b.creation).getTime() - new Date(a.creation).getTime()
        );

        const storedLinks = sessionStorage.getItem("pendingLinks");
        const linkMap = storedLinks ? JSON.parse(storedLinks) : {};

        const cancelPromises = transactions
          .filter((txn: any) => txn.status === "pending" && !linkMap[txn.transactionId])
          .map((txn: any) =>
            axios
              .put(`/api/v1/transaction/fiat/${txn.transactionId}`, { status: "cancelled" })
              .catch((err) => console.error("Failed to update txn to cancelled", err))
          );

        await Promise.all(cancelPromises);

        const updatedTransactions = transactions.map((txn: any) => {
          if (txn.status === "pending" && !linkMap[txn.transactionId]) {
            txn.status = "cancelled";
          }
          return txn;
        });

        setTransactions(updatedTransactions);
        setPendingLinks(linkMap);
      } catch (error) {
        console.error("Failed to load transactions", error);
      } finally {
        setDataLoading(false);
      }
    };

    const status = searchParams.get("status");
    if (status === "success") {
      setStatusMessage("success");
      setShowModal(true);
      window.history.replaceState(null, "", "/dashboard/deposit");
    }

    fetchFiatAccounts();
    fetchTransactions();
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!amount || Number.parseFloat(amount) <= 0) return;

    setIsProcessing(true);

    try {
      const userId = getCookie("userId");
      if (!userId) throw new Error("User not authenticated");

      const response = await axios.post("/api/v1/deposit/fiat/", {
        userId,
        amount: parseFloat(amount),
        currencyCode: currencyCode.toUpperCase() // Use the selected currency
      });

      const { checkoutUrl, transactionId } = response.data;
      const updatedLinks = { ...pendingLinks, [transactionId]: checkoutUrl };
      setPendingLinks(updatedLinks);
      sessionStorage.setItem("pendingLinks", JSON.stringify(updatedLinks));

      window.location.href = checkoutUrl;
    } catch (err: any) {
      console.error("Deposit initiation failed", err);
      alert("Deposit failed: " + (err.response?.data?.message || "Unknown error"));
    } finally {
      setIsProcessing(false);
    }
  };

  if (dataLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center">
          <p>Loading your account data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full px-4 lg:px-12 max-w-screen-xl grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <Dialog open={showModal} onOpenChange={setShowModal}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {statusMessage === "success" ? "Payment Successful" : null}
              </DialogTitle>
              {statusMessage === "success" && (
                <p className="text-sm text-muted-foreground">
                  Your funds will be available shortly.
                </p>
              )}
            </DialogHeader>
          </DialogContent>
        </Dialog>
        
        <div>
          <h2 className="text-lg font-semibold mb-2">Deposit Section</h2>
          <Card>
            <CardHeader>
              <CardTitle>Deposit Funds</CardTitle>
              <CardDescription>Add funds to your account using your preferred payment method</CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-6">
                {/* Currency Selector */}
                <div className="space-y-2">
                  <Label htmlFor="currency">Currency</Label>
                  <Select 
                    value={currencyCode} 
                    onValueChange={setCurrencyCode}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select Currency" />
                    </SelectTrigger>
                    <SelectContent>
                      {FIAT_CURRENCIES.map((currency) => (
                        <SelectItem key={currency.currencyCode} value={currency.currencyCode}>
                          {currency.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="amount">Amount ({currencyCode.toUpperCase()})</Label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                      {getCurrencySymbol()}
                    </span>
                    <Input
                      id="amount"
                      type="number"
                      placeholder="0.00"
                      className="pl-10"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      min="10"
                      step="0.01"
                      required
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">Minimum deposit: {getCurrencySymbol()}10.00</p>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label>Payment Method</Label>
                  <RadioGroup value={paymentMethod} onValueChange={setPaymentMethod} className="grid grid-cols-1 gap-4">
                    <div>
                      <RadioGroupItem value="credit-card" id="credit-card" className="peer sr-only" />
                      <Label
                        htmlFor="credit-card"
                        className="flex cursor-pointer items-center justify-between rounded-md border border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary"
                      >
                        <div className="flex items-center gap-2">
                          <CreditCard className="h-5 w-5" />
                          <div className="grid gap-1">
                            <div className="font-medium">Credit / Debit Card</div>
                            <div className="text-xs text-muted-foreground">Visa, Mastercard, AMEX</div>
                          </div>
                        </div>
                      </Label>
                    </div>
                  </RadioGroup>
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isProcessing || !amount || Number.parseFloat(amount) <= 0}
                >
                  {isProcessing ? "Processing..." : "Proceed to Payment"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </div>

        {fiatAccounts.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold mt-6">Your Fiat Accounts</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {fiatAccounts.map((account: any) => (
                <Card key={account.currencyCode} className="flex flex-col items-center text-center">
                  <CardHeader>
                    <CardTitle>{account.currencyCode.toUpperCase()}</CardTitle>
                    <CardDescription>Balance</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">
                      {FIAT_CURRENCIES.find(c => c.currencyCode.toLowerCase() === account.currencyCode.toLowerCase())?.symbol || '$'}
                      {account.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {transactions.length > 0 && (
        <div className="space-y-2 overflow-y-auto max-h-[80vh]">
          <h2 className="text-lg font-semibold">Recent Transactions</h2>
          <div className="space-y-2">
            {transactions.map((txn: any) => (
              <Card key={txn.transactionId} className="flex flex-col">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-sm">{txn.type.toUpperCase()}</CardTitle>
                    <CardDescription>
                      {txn.currencyCode.toUpperCase()} • {new Date(txn.creation).toLocaleString()}
                    </CardDescription>
                  </div>
                  <div className={`text-sm font-semibold ${txn.status === 'completed' ? 'text-green-600' : txn.status === 'cancelled' ? 'text-red-600' : 'text-yellow-600'}`}>
                    {txn.status.toUpperCase()}
                  </div>
                </CardHeader>
                <CardContent className="flex items-center justify-between">
                  <div className="text-xl font-bold">
                    {FIAT_CURRENCIES.find(c => c.currencyCode.toLowerCase() === txn.currencyCode.toLowerCase())?.symbol || '$'}
                    {txn.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                  {txn.status === "pending" && pendingLinks[txn.transactionId] && (
                    <Button size="sm" onClick={() => window.location.href = pendingLinks[txn.transactionId]}>Continue Payment</Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}