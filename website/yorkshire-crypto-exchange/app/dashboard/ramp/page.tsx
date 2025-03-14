"use client"

import type React from "react"

import { useState } from "react"
import { ArrowDown, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export default function RampPage() {
  const [fromAmount, setFromAmount] = useState("")
  const [fromCurrency, setFromCurrency] = useState("SGD")
  const [toCurrency, setToCurrency] = useState("USDT")
  const [isSwapping, setIsSwapping] = useState(false)

  // Mock exchange rate
  const exchangeRate = fromCurrency === "SGD" ? 0.75 : 1.33

  const toAmount = fromAmount ? (Number.parseFloat(fromAmount) * exchangeRate).toFixed(2) : ""

  const handleSwapPositions = () => {
    setFromCurrency(toCurrency)
    setToCurrency(fromCurrency)
    setFromAmount(toAmount)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!fromAmount || Number.parseFloat(fromAmount) <= 0) {
      return
    }

    setIsSwapping(true)

    // In a real app, you would call your API to perform the swap
    // For demo purposes, we'll simulate a successful swap after a delay
    setTimeout(() => {
      setIsSwapping(false)
      setFromAmount("")
    }, 2000)
  }

  return (
    <div className="mx-auto max-w-md">
      <Card>
        <CardHeader>
          <CardTitle>Ramp Exchange</CardTitle>
          <CardDescription>Swap between fiat and crypto currencies</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-8">
            <div className="space-y-2">
              <Label>From</Label>
              <div className="flex gap-2">
                <div className="flex-1">
                  <Input
                    type="number"
                    placeholder="0.00"
                    value={fromAmount}
                    onChange={(e) => setFromAmount(e.target.value)}
                    min="0"
                    step="0.01"
                    required
                  />
                </div>
                <Select value={fromCurrency} onValueChange={setFromCurrency}>
                  <SelectTrigger className="w-[120px]">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SGD">SGD</SelectItem>
                    <SelectItem value="USDT">USDT</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {fromCurrency === "SGD" && <p className="text-xs text-muted-foreground">Available: 5,000.00 SGD</p>}
              {fromCurrency === "USDT" && <p className="text-xs text-muted-foreground">Available: 1,000.00 USDT</p>}
            </div>

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

            <div className="space-y-2">
              <Label>To</Label>
              <div className="flex gap-2">
                <div className="flex-1">
                  <Input type="number" placeholder="0.00" value={toAmount} readOnly />
                </div>
                <Select value={toCurrency} onValueChange={setToCurrency}>
                  <SelectTrigger className="w-[120px]">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SGD">SGD</SelectItem>
                    <SelectItem value="USDT">USDT</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="rounded-md bg-muted p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Exchange Rate</span>
                <span>
                  1 {fromCurrency} = {exchangeRate} {toCurrency}
                </span>
              </div>
              {fromAmount && (
                <div className="mt-2 flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">You will receive</span>
                  <span className="font-medium">
                    {toAmount} {toCurrency}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={isSwapping || !fromAmount || Number.parseFloat(fromAmount) <= 0}
            >
              {isSwapping ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Swapping...
                </>
              ) : (
                "Swap"
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}

