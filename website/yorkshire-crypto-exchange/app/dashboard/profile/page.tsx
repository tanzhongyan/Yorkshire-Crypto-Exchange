"use client"

import type React from "react"

import { useState } from "react"
import { Save } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function ProfilePage() {
  const [personalInfo, setPersonalInfo] = useState({
    username: "cryptouser",
    fullname: "John Doe",
    email: "john.doe@example.com",
    phone: "+65 9123 4567",
  })

  const [address, setAddress] = useState({
    streetNumber: "123",
    streetName: "Orchard Road",
    unitNumber: "#05-01",
    buildingName: "Crypto Tower",
    district: "Central",
    city: "Singapore",
    stateProvince: "Singapore",
    postalCode: "238861",
    country: "Singapore",
  })

  const [security, setSecurity] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  })

  const [notifications, setNotifications] = useState({
    email: true,
    sms: true,
    push: false,
  })

  const handlePersonalInfoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setPersonalInfo((prev) => ({ ...prev, [name]: value }))
  }

  const handleAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setAddress((prev) => ({ ...prev, [name]: value }))
  }

  const handleSecurityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setSecurity((prev) => ({ ...prev, [name]: value }))
  }

  const handleNotificationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target
    setNotifications((prev) => ({ ...prev, [name]: checked }))
  }

  const handlePersonalInfoSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In a real app, you would call your API to update the user's personal info
    alert("Personal information updated successfully!")
  }

  const handleAddressSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In a real app, you would call your API to update the user's address
    alert("Address updated successfully!")
  }

  const handleSecuritySubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (security.newPassword !== security.confirmPassword) {
      alert("New passwords do not match!")
      return
    }

    // In a real app, you would call your API to update the user's password
    alert("Password updated successfully!")
    setSecurity({
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    })
  }

  const handleNotificationsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In a real app, you would call your API to update the user's notification preferences
    alert("Notification preferences updated successfully!")
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile Settings</h1>
        <p className="text-muted-foreground">Manage your account settings and preferences</p>
      </div>

      <Tabs defaultValue="personal" className="space-y-4">
        <TabsList>
          <TabsTrigger value="personal">Personal Info</TabsTrigger>
          <TabsTrigger value="address">Address</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="personal">
          <Card>
            <form onSubmit={handlePersonalInfoSubmit}>
              <CardHeader>
                <CardTitle>Personal Information</CardTitle>
                <CardDescription>Update your personal details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <Input
                      id="username"
                      name="username"
                      value={personalInfo.username}
                      onChange={handlePersonalInfoChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="fullname">Full Name</Label>
                    <Input
                      id="fullname"
                      name="fullname"
                      value={personalInfo.fullname}
                      onChange={handlePersonalInfoChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      value={personalInfo.email}
                      onChange={handlePersonalInfoChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input id="phone" name="phone" value={personalInfo.phone} onChange={handlePersonalInfoChange} />
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <Button type="submit">
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>

        <TabsContent value="address">
          <Card>
            <form onSubmit={handleAddressSubmit}>
              <CardHeader>
                <CardTitle>Address</CardTitle>
                <CardDescription>Update your address information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="streetNumber">Street Number</Label>
                    <Input
                      id="streetNumber"
                      name="streetNumber"
                      value={address.streetNumber}
                      onChange={handleAddressChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="streetName">Street Name</Label>
                    <Input
                      id="streetName"
                      name="streetName"
                      value={address.streetName}
                      onChange={handleAddressChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="unitNumber">Unit Number</Label>
                    <Input
                      id="unitNumber"
                      name="unitNumber"
                      value={address.unitNumber}
                      onChange={handleAddressChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="buildingName">Building Name</Label>
                    <Input
                      id="buildingName"
                      name="buildingName"
                      value={address.buildingName}
                      onChange={handleAddressChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="district">District</Label>
                    <Input id="district" name="district" value={address.district} onChange={handleAddressChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="city">City</Label>
                    <Input id="city" name="city" value={address.city} onChange={handleAddressChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stateProvince">State/Province</Label>
                    <Input
                      id="stateProvince"
                      name="stateProvince"
                      value={address.stateProvince}
                      onChange={handleAddressChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="postalCode">Postal Code</Label>
                    <Input
                      id="postalCode"
                      name="postalCode"
                      value={address.postalCode}
                      onChange={handleAddressChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">Country</Label>
                    <Input id="country" name="country" value={address.country} onChange={handleAddressChange} />
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <Button type="submit">
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <form onSubmit={handleSecuritySubmit}>
              <CardHeader>
                <CardTitle>Security</CardTitle>
                <CardDescription>Update your password and security settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <Input
                    id="currentPassword"
                    name="currentPassword"
                    type="password"
                    value={security.currentPassword}
                    onChange={handleSecurityChange}
                    required
                  />
                </div>
                <Separator />
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <Input
                    id="newPassword"
                    name="newPassword"
                    type="password"
                    value={security.newPassword}
                    onChange={handleSecurityChange}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    value={security.confirmPassword}
                    onChange={handleSecurityChange}
                    required
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Button type="submit">
                  <Save className="mr-2 h-4 w-4" />
                  Update Password
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <form onSubmit={handleNotificationsSubmit}>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>Choose how you want to receive notifications</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="email-notifications"
                    name="email"
                    checked={notifications.email}
                    onChange={handleNotificationChange}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <Label htmlFor="email-notifications">Email Notifications</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="sms-notifications"
                    name="sms"
                    checked={notifications.sms}
                    onChange={handleNotificationChange}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <Label htmlFor="sms-notifications">SMS Notifications</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="push-notifications"
                    name="push"
                    checked={notifications.push}
                    onChange={handleNotificationChange}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <Label htmlFor="push-notifications">Push Notifications</Label>
                </div>
              </CardContent>
              <CardFooter>
                <Button type="submit">
                  <Save className="mr-2 h-4 w-4" />
                  Save Preferences
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

