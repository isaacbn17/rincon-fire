import { Link } from "react-router-dom"

export function NotFoundPage() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-2 p-6 text-center">
      <h1 className="text-3xl font-bold">404</h1>
      <p className="text-muted-foreground">The page you requested was not found.</p>
      <Link className="underline" to="/">
        Return to dashboard
      </Link>
    </div>
  )
}
