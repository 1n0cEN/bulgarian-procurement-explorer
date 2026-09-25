"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="page">
      <h1>Something went wrong</h1>
      <p>The requested page could not be loaded.</p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
