"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CreditCard, Copy, Check, AlertCircle } from "lucide-react";

import { getCookie } from "@/lib/cookies";
import axios from "@/lib/axios";
import { AxiosError } from 'axios';
import { Button } from "@/components/ui/button";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface PendingLinks {
  [transactionId: string]: string;
}

interface Transaction {
  transactionId: string;
  status: string;
  type: string;
  currencyCode: string;
  amount: number;
  creation: string;
}

interface FiatAccount {
  currencyCode: string;
  balance: number;
}

// Define available currencies with their symbols and maximum limits
const FIAT_CURRENCIES = [
  {
    currencyCode: "usd",
    name: "US Dollar (USD)",
    symbol: "$",
    maxLimit: 999999.99,
  },
  {
    currencyCode: "sgd",
    name: "Singapore Dollar (SGD)",
    symbol: "S$",
    maxLimit: 999999.99,
  },
  { currencyCode: "eur", name: "Euro (EUR)", symbol: "€", maxLimit: 999999.99 },
  {
    currencyCode: "myr",
    name: "Malaysian Ringgit (MYR)",
    symbol: "RM",
    maxLimit: 999999.99,
  },
  {
    currencyCode: "aud",
    name: "Australian Dollar (AUD)",
    symbol: "A$",
    maxLimit: 999999.99,
  },
  {
    currencyCode: "gbp",
    name: "British Pound (GBP)",
    symbol: "£",
    maxLimit: 999999.99,
  },
  {
    currencyCode: "jpy",
    name: "Japanese Yen (JPY)",
    symbol: "¥",
    maxLimit: 999999.99,
  },
  {
    currencyCode: "cny",
    name: "Chinese Yuan (CNY)",
    symbol: "¥",
    maxLimit: 999999.99,
  },
  {
    currencyCode: "inr",
    name: "Indian Rupee (INR)",
    symbol: "₹",
    maxLimit: 9999999.99,
  },
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
  const [pendingLinks, setPendingLinks] = useState<PendingLinks>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [showTestCardWarning, setShowTestCardWarning] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const searchParams = useSearchParams();

  // Calculate test card expiry date (5 years from now)
  const getTestCardExpiry = () => {
    const now = new Date();
    const futureYear = now.getFullYear() + 5;
    const month = String(now.getMonth() + 1).padStart(2, "0");
    return `${month}/${String(futureYear).slice(-2)}`;
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopyFeedback(label);
      setTimeout(() => setCopyFeedback(null), 2000);
    });
  };

  // Get the currency details for the selected currency
  const getCurrencyDetails = () => {
    return (
      FIAT_CURRENCIES.find((c) => c.currencyCode === currencyCode) ||
      FIAT_CURRENCIES[0]
    );
  };

  // Get the currency symbol for the selected currency
  const getCurrencySymbol = () => {
    return getCurrencyDetails().symbol;
  };

  // Get the maximum limit for the selected currency
  const getCurrencyMaxLimit = () => {
    return getCurrencyDetails().maxLimit;
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

        const response = await axios.get(
          `/api/v1/transaction/fiatuser/${userId}`,
        );
        const transactions = response.data.sort(
          (a: Transaction, b: Transaction) =>
            new Date(b.creation).getTime() - new Date(a.creation).getTime(),
        );

        const storedLinks = sessionStorage.getItem("pendingLinks");
        const linkMap = storedLinks ? JSON.parse(storedLinks) : {};

        const cancelPromises = transactions
          .filter(
            (txn: Transaction) =>
              txn.status === "pending" && !linkMap[txn.transactionId],
          )
          .map((txn: Transaction) =>
            axios
              .put(`/api/v1/transaction/fiat/${txn.transactionId}`, {
                status: "cancelled",
              })
              .catch((err) =>
                console.error("Failed to update txn to cancelled", err),
              ),
          );

        await Promise.all(cancelPromises);

        const updatedTransactions = transactions.map((txn: Transaction) => {
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

    const parsedAmount = parseFloat(amount);
    const maxLimit = getCurrencyMaxLimit();

    if (!amount || parsedAmount <= 0) return;
    if (parsedAmount > maxLimit) {
      alert(
        `Maximum deposit amount for ${currencyCode.toUpperCase()} is ${getCurrencySymbol()}${maxLimit.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
      );
      return;
    }

    // Show test card warning dialog before processing
    setShowTestCardWarning(true);
  };

  const handleConfirmPayment = async () => {
    setShowTestCardWarning(false);
    setIsProcessing(true);

    try {
      const userId = getCookie("userId");
      if (!userId) throw new Error("User not authenticated");

      const response = await axios.post("/api/v1/deposit/fiat/", {
        userId,
        amount: parsedAmount,
        currencyCode: currencyCode.toUpperCase(), // Use the selected currency
      });

      const { checkoutUrl, transactionId } = response.data;
      const updatedLinks = { ...pendingLinks, [transactionId]: checkoutUrl };
      setPendingLinks(updatedLinks);
      sessionStorage.setItem("pendingLinks", JSON.stringify(updatedLinks));

      window.location.href = checkoutUrl;
    } catch (err: unknown) {
      if (err instanceof AxiosError) {
        console.error("Deposit initiation failed", err);
        alert(
          "Deposit failed: " + (err.response?.data?.message || "Unknown error")
        );
      } else {
        // Handle other types of errors here
        console.error("An unexpected error occurred:", err);
      }
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

        {/* Test Card Warning Dialog */}
        <Dialog open={showTestCardWarning} onOpenChange={setShowTestCardWarning}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Test Payment Card</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                This is a development environment. Please use the following test credit card details for payments. No real money will be charged.
              </p>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
                <div>
                  <p className="text-xs font-semibold text-slate-700 mb-2">Card Number</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm text-slate-900 font-mono flex-1">4242 4242 4242 4242</p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyToClipboard("4242424242424242", "Card number")}
                      className="h-8 px-2"
                      title="Copy card number"
                    >
                      {copyFeedback === "Card number" ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-semibold text-slate-700 mb-2">Expiry</p>
                    <div className="flex items-center gap-2">
                      <p className="text-sm text-slate-900 font-mono flex-1">{getTestCardExpiry()}</p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => copyToClipboard(getTestCardExpiry(), "Expiry")}
                        className="h-8 px-2"
                        title="Copy expiry date"
                      >
                        {copyFeedback === "Expiry" ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-slate-700 mb-2">CVV</p>
                    <div className="flex items-center gap-2">
                      <p className="text-sm text-slate-900 font-mono flex-1">123</p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => copyToClipboard("123", "CVV")}
                        className="h-8 px-2"
                        title="Copy CVV"
                      >
                        {copyFeedback === "CVV" ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg p-3">
                <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-amber-800">
                  This is a testing environment. No real charges will be made to your account.
                </p>
              </div>
            </div>

            <div className="flex gap-2 justify-end pt-2">
              <Button
                variant="outline"
                onClick={() => setShowTestCardWarning(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirmPayment}
                disabled={isProcessing}
              >
                {isProcessing ? "Processing..." : "I Understand, Continue"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        <div>
          <h2 className="text-lg font-semibold mb-2">Deposit Section</h2>
          <Card>
            <CardHeader>
              <CardTitle>Deposit Funds</CardTitle>
              <CardDescription>
                Add funds to your account using your preferred payment method
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-6">
                {/* Currency Selector */}
                <div className="space-y-2">
                  <Label htmlFor="currency">Currency</Label>
                  <Select value={currencyCode} onValueChange={setCurrencyCode}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select Currency" />
                    </SelectTrigger>
                    <SelectContent>
                      {FIAT_CURRENCIES.map((currency) => (
                        <SelectItem
                          key={currency.currencyCode}
                          value={currency.currencyCode}
                        >
                          {currency.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="amount">
                    Amount ({currencyCode.toUpperCase()})
                  </Label>
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
                      onChange={(e) => {
                        const value = e.target.value;
                        const maxLimit = getCurrencyMaxLimit();
                        // Only update if the value is within limits or empty
                        if (!value || parseFloat(value) <= maxLimit) {
                          setAmount(value);
                        }
                      }}
                      min="10"
                      max={getCurrencyMaxLimit()}
                      step="0.01"
                      required
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Minimum deposit: {getCurrencySymbol()}10.00 | Maximum
                    deposit: {getCurrencySymbol()}
                    {getCurrencyMaxLimit().toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                    })}
                  </p>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label>Payment Method</Label>
                  <RadioGroup
                    value={paymentMethod}
                    onValueChange={setPaymentMethod}
                    className="grid grid-cols-1 gap-4"
                  >
                    <div>
                      <RadioGroupItem
                        value="credit-card"
                        id="credit-card"
                        className="peer sr-only"
                      />
                      <Label
                        htmlFor="credit-card"
                        className="flex cursor-pointer items-center justify-between rounded-md border border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary"
                      >
                        <div className="flex items-center gap-2">
                          <CreditCard className="h-5 w-5" />
                          <div className="grid gap-1">
                            <div className="font-medium">
                              Credit / Debit Card
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Visa, Mastercard, AMEX
                            </div>
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
                  disabled={
                    isProcessing ||
                    !amount ||
                    parseFloat(amount) <= 0 ||
                    parseFloat(amount) > getCurrencyMaxLimit()
                  }
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
              {fiatAccounts.map((account: FiatAccount) => (
                <Card
                  key={account.currencyCode}
                  className="flex flex-col items-center text-center"
                >
                  <CardHeader>
                    <CardTitle>{account.currencyCode.toUpperCase()}</CardTitle>
                    <CardDescription>Balance</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">
                      {FIAT_CURRENCIES.find(
                        (c) =>
                          c.currencyCode.toLowerCase() ===
                          account.currencyCode.toLowerCase(),
                      )?.symbol || "$"}
                      {account.balance.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                      })}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="space-y-2 overflow-y-auto max-h-[80vh]">
        <h2 className="text-lg font-semibold">Fiat Transactions</h2>
        {transactions.length > 0 ? (
          <div className="space-y-2">
            {transactions.map((txn: Transaction) => (
              <Card key={txn.transactionId} className="flex flex-col">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-sm">
                      {txn.type.toUpperCase()}
                    </CardTitle>
                    <CardDescription>
                      {txn.currencyCode.toUpperCase()} •{" "}
                      {new Date(txn.creation).toLocaleString()}
                    </CardDescription>
                  </div>
                  <div
                    className={`text-sm font-semibold ${txn.status === "completed" ? "text-green-600" : txn.status === "cancelled" ? "text-red-600" : "text-yellow-600"}`}
                  >
                    {txn.status.toUpperCase()}
                  </div>
                </CardHeader>
                <CardContent className="flex items-center justify-between">
                  <div className="text-xl font-bold">
                    {FIAT_CURRENCIES.find(
                      (c) =>
                        c.currencyCode.toLowerCase() ===
                        txn.currencyCode.toLowerCase(),
                    )?.symbol || "$"}
                    {txn.amount.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                    })}
                  </div>
                  {txn.status === "pending" &&
                    pendingLinks[txn.transactionId] && (
                      <Button
                        size="sm"
                        onClick={() =>
                          (window.location.href =
                            pendingLinks[txn.transactionId])
                        }
                      >
                        Continue Payment
                      </Button>
                    )}
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <p>No deposit transactions yet</p>
          </div>
        )}
      </div>
    </div>
  );
}
