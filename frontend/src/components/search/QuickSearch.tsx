"use client"; 

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input"; 
import { Search } from "lucide-react"; 

export function QuickSearch() {
  const router = useRouter();
  
  const [query, setQuery] = useState("");

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Trigger search on Enter key press
    if (e.key === "Enter" && query.trim()) {
      // Navigate to the search results page with the query as a URL parameter
      router.push(`/search?q=${encodeURIComponent(query)}`);
      // Clear the input field after navigating
      setQuery(""); 
    }
  };

  return (
    <div className="relative w-full max-w-sm ml-auto mr-4">
      
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      
      <Input
        type="search"
        placeholder="Quick search..." 
        className="w-full pl-9 bg-background" 
        value={query} 
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown} 
      />
    </div>
  );
}