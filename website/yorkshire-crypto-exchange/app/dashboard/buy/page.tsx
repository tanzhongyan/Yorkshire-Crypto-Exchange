"use client"

import type React from "react";
import { getCookie } from '@/lib/cookies';

import { useState } from "react"
import { ArrowUp } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"

// Mock order book data
const asks = [
  { price: 65250.0, amount: 0.5, total: 32625.0 },
  { price: 65200.0, amount: 0.8, total: 52160.0 },
  { price: 65150.0, amount: 1.2, total: 78180.0 },
  { price: 65100.0, amount: 0.3, total: 19530.0 },
  { price: 65050.0, amount: 0.7, total: 45535.0 },
]

const bids = [
  { price: 65000.0, amount: 0.4, total: 26000.0 },
  { price: 64950.0, amount: 0.6, total: 38970.0 },
  { price: 64900.0, amount: 1.0, total: 64900.0 },
  { price: 64850.0, amount: 0.2, total: 12970.0 },
  { price: 64800.0, amount: 0.9, total: 58320.0 },
]

// Mock recent trades
const recentTrades = [
  { price: 65100.0, amount: 0.12, time: "14:45:32", type: "buy" },
  { price: 65050.0, amount: 0.08, time: "14:44:15", type: "sell" },
  { price: 65100.0, amount: 0.25, time: "14:43:22", type: "buy" },
  { price: 65000.0, amount: 0.15, time: "14:42:10", type: "sell" },
  { price: 64950.0, amount: 0.3, time: "14:41:05", type: "sell" },
]

export default function BuyPage() {
  const [orderType, setOrderType] = useState("limit")
  const [buyPrice, setBuyPrice] = useState("65000.00") 
  const [buyAmount, setBuyAmount] = useState("")
  const [sellPrice, setSellPrice] = useState("65100.00")
  const [sellAmount, setSellAmount] = useState("")
  const [selectedPair, setSelectedPair] = useState("BTC/USDT")

  const buyTotal =
    buyPrice && buyAmount ? (Number.parseFloat(buyPrice) * Number.parseFloat(buyAmount)).toFixed(2) : "0.00"
  const sellTotal =
    sellPrice && sellAmount ? (Number.parseFloat(sellPrice) * Number.parseFloat(sellAmount)).toFixed(2) : "0.00"

  // (1) Buy - sends form to backend for processing
  const handleBuySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log(e.target)

    const fromTokenId = selectedPair.split("/")[0]
    const toTokenId = selectedPair.split("/")[1]
    const userId = getCookie('userId')

    const data = {
      "userId": userId,
      "fromTokenId": fromTokenId,
      "toTokenId": toTokenId,
      "fromAmount": buyAmount,
      "limitPrice": buyPrice,
      "orderType": orderType,
    }
    console.log("data", data)
    // In a real app, you would call your API to place the buy order
    // alert(`Buy order placed: ${buyAmount} BTC at $${buyPrice}`)
    setBuyAmount("")
  }

  // (2) Sell (ignored)
  const handleSellSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In a real app, you would call your API to place the sell order
    alert(`Sell order placed: ${sellAmount} BTC at $${sellPrice}`)
    setSellAmount("")
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-6">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>BTC/USDT</CardTitle>
                <CardDescription>Bitcoin to Tether</CardDescription>
              </div>
              <Select value={selectedPair} onValueChange={setSelectedPair}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Select pair" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BTC/USDT">BTC/USDT</SelectItem>
                  <SelectItem value="ETH/USDT">ETH/USDT</SelectItem>
                  <SelectItem value="BNB/USDT">BNB/USDT</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$65,100.00</div>
            <div className="flex items-center text-green-500 text-sm">
              <ArrowUp className="mr-1 h-4 w-4" />
              2.5% (24h)
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
                    <div className="text-right">Amount (BTC)</div>
                    <div className="text-right">Total (USDT)</div>
                  </div>
                  <div className="space-y-1">
                    {asks.map((ask, index) => (
                      <div key={index} className="grid grid-cols-3 text-xs text-red-500">
                        <div>{ask.price.toFixed(2)}</div>
                        <div className="text-right">{ask.amount.toFixed(2)}</div>
                        <div className="text-right">{ask.total.toFixed(2)}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="py-2 text-center font-bold text-lg">$65,100.00</div>

                <div>
                  <div className="space-y-1">
                    {bids.map((bid, index) => (
                      <div key={index} className="grid grid-cols-3 text-xs text-green-500">
                        <div>{bid.price.toFixed(2)}</div>
                        <div className="text-right">{bid.amount.toFixed(2)}</div>
                        <div className="text-right">{bid.total.toFixed(2)}</div>
                      </div>
                    ))}
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
                  <div className="text-right">Amount (BTC)</div>
                  <div className="text-right">Total (USDT)</div>
                  <div className="text-right">Time</div>
                </div>
                <div className="space-y-2">
                  {recentTrades.map((trade, index) => (
                    <div
                      key={index}
                      className={`grid grid-cols-4 text-xs ${trade.type === "buy" ? "text-green-500" : "text-red-500"}`}
                    >
                      <div>{trade.price.toFixed(2)}</div>
                      <div className="text-right">{trade.amount.toFixed(2)}</div>
                      <div className="text-right">{(trade.price * trade.amount).toFixed(2)}</div>
                      <div className="text-right">{trade.time}</div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Place Order</CardTitle>
            <div className="flex space-x-2">
              <Button
                variant={orderType === "limit" ? "default" : "outline"}
                size="sm"
                onClick={() => setOrderType("limit")}
              >
                Limit
              </Button>
              <Button
                variant={orderType === "market" ? "default" : "outline"}
                size="sm"
                onClick={() => setOrderType("market")}
              >
                Market
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
                        {/* to be dynamic */}
                        <Label htmlFor="buy-price">Price (USDT)</Label>
                        <Input
                          id="buy-price"
                          type="number"
                          step="0.01"
                          value={buyPrice}
                          onChange={(e) => setBuyPrice(e.target.value)}
                          required
                        />
                      </div>
                    )}
                    <div className="space-y-2">
                      {/* to be static */}
                      <Label htmlFor="buy-amount">Amount (BTC)</Label> 
                      <Input
                        id="buy-amount"
                        type="number"
                        step="0.0001"
                        placeholder="0.00"
                        value={buyAmount}
                        onChange={(e) => setBuyAmount(e.target.value)}
                        required
                      />
                    </div>
                    <Separator />
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Total</span>
                      <span>{buyTotal} USDT</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Available</span>
                      <span>1,000.00 USDT</span>
                    </div>
                    <Button type="submit" className="w-full bg-green-600 hover:bg-green-700">
                      Buy BTC
                    </Button>
                  </div>
                </form>
              </TabsContent>
              <TabsContent value="sell" className="space-y-4 pt-4">
                <form onSubmit={handleSellSubmit}>
                  <div className="space-y-4">
                    {orderType === "limit" && (
                      <div className="space-y-2">
                        <Label htmlFor="sell-price">Price (USDT)</Label>
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
                      <Label htmlFor="sell-amount">Amount (BTC)</Label>
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
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Total</span>
                      <span>{sellTotal} USDT</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Available</span>
                      <span>0.05 BTC</span>
                    </div>
                    <Button type="submit" className="w-full bg-red-600 hover:bg-red-700">
                      Sell BTC
                    </Button>
                  </div>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

