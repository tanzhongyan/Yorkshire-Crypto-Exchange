"use client"

import { useEffect, useState } from "react"
import { AlertCircle, Save, Trash2, Eye, EyeOff } from "lucide-react"
import { getCookie } from "@/lib/cookies"
import axios from "@/lib/axios"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { 
  Dialog,
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle,
  DialogTrigger, 
} from "@/components/ui/dialog"

export default function ProfilePage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteConfirmation, setDeleteConfirmation] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  const [personalInfo, setPersonalInfo] = useState({
    username: "",
    fullname: "",
    email: "",
    phone: "",
  })

  // Address tab is commented out
  /*
  const [address, setAddress] = useState({
    streetNumber: "",
    streetName: "",
    unitNumber: "",
    buildingName: "",
    district: "",
    city: "",
    stateProvince: "",
    postalCode: "",
    country: "",
  })
  */

  const [security, setSecurity] = useState({
    newPassword: "",
    confirmPassword: "",
  })

  const [notifications, setNotifications] = useState({
    email: true,
    sms: true,
    push: false,
  })

  const userId = getCookie("userId")

  // Fetch user data on component mount
  useEffect(() => {
    if (!userId) {
      setError("User not authenticated")
      setLoading(false)
      return
    }

    const fetchUserData = async () => {
      try {
        setLoading(true)
        const response = await axios.get(`/api/v1/user/account/${userId}`)
        
        setPersonalInfo({
          username: response.data.username || "",
          fullname: response.data.fullname || "",
          email: response.data.email || "",
          phone: response.data.phone || "",
        })
        
        setLoading(false)
      } catch (err: any) {
        console.error("Failed to fetch user data:", err)
        setError(err.response?.data?.message || "Failed to load user data")
        setLoading(false)
      }
    }

    fetchUserData()
  }, [userId])

  const handlePersonalInfoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setPersonalInfo((prev) => ({ ...prev, [name]: value }))
  }

  // Address tab is commented out
  /*
  const handleAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setAddress((prev) => ({ ...prev, [name]: value }))
  }
  */

  const handleSecurityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setSecurity((prev) => ({ ...prev, [name]: value }))
  }

  const handleNotificationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target
    setNotifications((prev) => ({ ...prev, [name]: checked }))
  }

  const handlePersonalInfoSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!userId) {
      setError("User not authenticated")
      return
    }

    try {
      setLoading(true)
      await axios.put(`/api/v1/user/account/${userId}`, {
        username: personalInfo.username,
        fullname: personalInfo.fullname,
        email: personalInfo.email,
        phone: personalInfo.phone,
      })
      
      setSuccess("Personal information updated successfully!")
      setTimeout(() => setSuccess(null), 3000)
      setLoading(false)
    } catch (err: any) {
      console.error("Failed to update personal info:", err)
      setError(err.response?.data?.message || "Failed to update personal information")
      setLoading(false)
    }
  }

  // Address tab is commented out
  /*
  const handleAddressSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In a real app, you would call your API to update the user's address
    alert("Address updated successfully!")
  }
  */

  const handleSecuritySubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!userId) {
      setError("User not authenticated")
      return
    }

    if (security.newPassword !== security.confirmPassword) {
      setError("New passwords do not match!")
      return
    }

    try {
      setLoading(true)
      await axios.put(`/api/v1/user/authenticate/${userId}`, {
        password: security.newPassword
      })
      
      setSuccess("Password updated successfully!")
      setSecurity({
        newPassword: "",
        confirmPassword: "",
      })
      setTimeout(() => setSuccess(null), 3000)
      setLoading(false)
    } catch (err: any) {
      console.error("Failed to update password:", err)
      setError(err.response?.data?.message || "Failed to update password")
      setLoading(false)
    }
  }

  const handleNotificationsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In a real app, you would call your API to update the user's notification preferences
    setSuccess("Notification preferences updated successfully!")
    setTimeout(() => setSuccess(null), 3000)
  }

  const handleDeleteAccount = async () => {
    if (!userId) {
      setError("User not authenticated")
      return
    }

    if (deleteConfirmation !== "delete") {
      setError("Please type 'delete' to confirm account deletion")
      return
    }

    try {
      setLoading(true)
      await axios.post(`/api/v1/identity/delete-account`, {
        userId: userId
      })
      
      // Clear cookies and redirect to homepage
      document.cookie = "userId=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"
      document.cookie = "jwt_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"
      
      window.location.href = "/"
    } catch (err: any) {
      console.error("Failed to delete account:", err)
      setError(err.response?.data?.message || "Failed to delete account")
      setLoading(false)
      setDeleteDialogOpen(false)
      setDeleteConfirmation("")
    }
  }

  if (loading && !personalInfo.username) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <p>Loading your profile...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile Settings</h1>
        <p className="text-muted-foreground">Manage your account settings and preferences</p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="bg-green-50 text-green-800 border-green-200">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="personal" className="space-y-4">
        <TabsList>
          <TabsTrigger value="personal">Personal Info</TabsTrigger>
          {/* <TabsTrigger value="address">Address</TabsTrigger> */}
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
              <CardFooter className="flex justify-between">
                <Button type="submit" disabled={loading}>
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </Button>
                
                <Dialog open={deleteDialogOpen} onOpenChange={(open) => {
                  setDeleteDialogOpen(open);
                  if (!open) setDeleteConfirmation("");
                }}>
                  <DialogTrigger asChild>
                    <Button variant="destructive">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete Account
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Are you sure you want to delete your account?</DialogTitle>
                      <DialogDescription>
                        This action cannot be undone. It will permanently delete your account and remove all your data from our servers.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="mt-4">
                      <Label htmlFor="delete-confirmation">Type "delete" to confirm:</Label>
                      <Input 
                        id="delete-confirmation"
                        value={deleteConfirmation}
                        onChange={(e) => setDeleteConfirmation(e.target.value)}
                        className="mt-2"
                      />
                    </div>
                    <DialogFooter className="mt-4">
                      <Button variant="outline" onClick={() => {
                        setDeleteConfirmation("");
                        setDeleteDialogOpen(false);
                      }}>
                        Cancel
                      </Button>
                      <Button 
                        variant="destructive" 
                        onClick={handleDeleteAccount} 
                        disabled={loading || deleteConfirmation !== "delete"}
                      >
                        {loading ? "Deleting..." : "Delete Account"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>

        {/* Address tab is commented out 
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
        */}

        <TabsContent value="security">
          <Card>
            <form onSubmit={handleSecuritySubmit}>
              <CardHeader>
                <CardTitle>Security</CardTitle>
                <CardDescription>Update your password and security settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <div className="relative">
                    <Input
                      id="newPassword"
                      name="newPassword"
                      type={showPassword ? "text" : "password"}
                      value={security.newPassword}
                      onChange={handleSecurityChange}
                      required
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-2 top-1/2 -translate-y-1/2 h-7 px-2 py-0"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showPassword ? "text" : "password"}
                    value={security.confirmPassword}
                    onChange={handleSecurityChange}
                    required
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Button type="submit" disabled={loading}>
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
                <Button type="submit" disabled={loading}>
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