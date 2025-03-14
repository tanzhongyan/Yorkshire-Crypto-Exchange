import { redirect } from "next/navigation"

export default function Home() {
  // In a real app, you would check if the user is authenticated
  // For demo purposes, we'll redirect to the login page
  redirect("/login")
}

