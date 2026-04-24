import { useState } from "react";

interface Props {
  onSubmit: (key: string) => void;
}

export default function ApiKeyPrompt({ onSubmit }: Props) {
  const [value, setValue] = useState("");

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold text-gray-900 mb-1">RazorScope</h1>
        <p className="text-sm text-gray-500 mb-6">Enter your API key to view the dashboard.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (value.trim()) onSubmit(value.trim());
          }}
          className="space-y-4"
        >
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="rzs_dev_11111111"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg"
          >
            Open Dashboard
          </button>
        </form>
      </div>
    </div>
  );
}
