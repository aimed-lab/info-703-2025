export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface Chat {
  id: string;
  name: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface SearchDetails {
  totalRecords: number;
  searchTerms: string[];
  conditions: { field: string; value: string }[];
  requestedColumns: string[];
  availableColumns: string[];
  sources: string[];
}

export interface SearchResult {
  text: string;
  foundInKnowledgeBase: boolean;
  searchDetails: SearchDetails;
  tableData?: {
    headers: string[];
    rows: any[][];
    caption?: string;
  };
}

export interface DataEntry {
  [key: string]: any;
  content: string;
  source: string;
}