"use client"

import type React from "react"

import { useState } from "react"
import { CreditCard } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Separator } from "@/components/ui/separator"

export default function DepositPage() {
  const [amount, setAmount] = useState("")
  const [paymentMethod, setPaymentMethod] = useState("credit-card")
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!amount || Number.parseFloat(amount) <= 0) {
      return
    }

    setIsProcessing(true)

    // In a real app, you would call your API to create a Stripe checkout session
    // For demo purposes, we'll simulate a successful payment after a delay
    setTimeout(() => {
      setIsProcessing(false)
      setIsSuccess(true)

      // Reset after showing success message
      setTimeout(() => {
        setIsSuccess(false)
        setAmount("")
      }, 3000)
    }, 2000)
  }

  return (
    <div className="mx-auto max-w-md">
      <Card>
        <CardHeader>
          <CardTitle>Deposit Funds</CardTitle>
          <CardDescription>Add funds to your account using your preferred payment method</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="amount">Amount (SGD)</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  id="amount"
                  type="number"
                  placeholder="0.00"
                  className="pl-8"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  min="10"
                  step="0.01"
                  required
                />
              </div>
              <p className="text-xs text-muted-foreground">Minimum deposit: $10.00</p>
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

            {isSuccess && (
              <div className="rounded-md bg-green-50 p-4 text-green-700">
                <p className="text-sm font-medium">Payment successful!</p>
                <p className="text-xs">Your funds will be available shortly.</p>
              </div>
            )}
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
  )
}

