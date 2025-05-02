import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { compress, decompress } from 'lz-string';
import { SearchResult, DataEntry } from '../types';
import { openai, defaultChatConfig } from './openai';

// Constants for localStorage keys and chunks
const CACHE_KEY_PREFIX = 'pharmalchemy_cached_data_chunk_';
const FILES_KEY = 'pharmalchemy_uploaded_files';
const CHUNK_SIZE = 50 * 1024; // 50KB chunks
const MAX_CHUNKS = 40; // More chunks since we're using compression
const CHUNK_COUNT_KEY = 'pharmalchemy_chunk_count';

let cachedData: DataEntry[] = [];
let userUploadedFiles: string[] = [];

function loadCachedData() {
  try {
    const savedFiles = localStorage.getItem(FILES_KEY);
    if (savedFiles) {
      userUploadedFiles = JSON.parse(savedFiles);
    }

    const chunkCount = parseInt(localStorage.getItem(CHUNK_COUNT_KEY) || '0', 10);
    cachedData = [];
    
    for (let i = 0; i < chunkCount; i++) {
      try {
        const compressedChunk = localStorage.getItem(`${CACHE_KEY_PREFIX}${i}`);
        if (compressedChunk) {
          const decompressedChunk = decompress(compressedChunk);
          if (decompressedChunk) {
            const parsedChunk = JSON.parse(decompressedChunk);
            if (Array.isArray(parsedChunk)) {
              cachedData.push(...parsedChunk);
            }
          }
        }
      } catch (chunkError) {
        console.warn(`Error loading chunk ${i}, skipping:`, chunkError);
      }
    }
  } catch (error) {
    console.error('Error loading cached data:', error);
    cachedData = [];
    userUploadedFiles = [];
  }
}

// Load data immediately
loadCachedData();

function saveCachedData() {
  try {
    localStorage.setItem(FILES_KEY, JSON.stringify(userUploadedFiles));

    const oldChunkCount = parseInt(localStorage.getItem(CHUNK_COUNT_KEY) || '0', 10);
    for (let i = 0; i < oldChunkCount; i++) {
      localStorage.removeItem(`${CACHE_KEY_PREFIX}${i}`);
    }

    const itemsPerChunk = Math.ceil(cachedData.length / MAX_CHUNKS);
    const chunks: DataEntry[][] = [];

    for (let i = 0; i < cachedData.length; i += itemsPerChunk) {
      chunks.push(cachedData.slice(i, i + itemsPerChunk));
    }

    chunks.forEach((chunk, index) => {
      try {
        const chunkString = JSON.stringify(chunk);
        const compressedChunk = compress(chunkString);
        localStorage.setItem(`${CACHE_KEY_PREFIX}${index}`, compressedChunk);
      } catch (chunkError) {
        console.error(`Error saving chunk ${index}:`, chunkError);
        const reducedChunk = chunk.slice(0, Math.floor(chunk.length * 0.7));
        const reducedString = JSON.stringify(reducedChunk);
        const compressedReduced = compress(reducedString);
        localStorage.setItem(`${CACHE_KEY_PREFIX}${index}`, compressedReduced);
      }
    });

    localStorage.setItem(CHUNK_COUNT_KEY, chunks.length.toString());
  } catch (error) {
    console.error('Error saving cached data:', error);
    try {
      const reducedData = cachedData.slice(-Math.floor(cachedData.length * 0.6));
      cachedData = reducedData;
      saveCachedData();
    } catch (retryError) {
      console.error('Failed to save even with reduced data:', retryError);
    }
  }
}

async function processExcelFile(file: File): Promise<DataEntry[]> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet);

        if (!Array.isArray(jsonData) || jsonData.length === 0) {
          throw new Error('No data found in Excel file');
        }

        const processedData = jsonData
          .filter((row: any) => Object.values(row).some(value => value != null && value !== ''))
          .map((row: any) => ({
            ...row,
            source: file.name,
            content: Object.entries(row)
              .filter(([_, value]) => value != null && value !== '')
              .map(([key, value]) => `${key}: ${value}`)
              .join(' | ')
          }));

        resolve(processedData);
      } catch (error) {
        reject(new Error('Error processing Excel file'));
      }
    };
    reader.onerror = () => reject(new Error('Error reading file'));
    reader.readAsArrayBuffer(file);
  });
}

async function processCsvFile(file: File | string): Promise<DataEntry[]> {
  try {
    let text: string;
    if (typeof file === 'string') {
      const response = await fetch(`/data/${file}`);
      if (!response.ok) {
        throw new Error(`Failed to load file: ${file}`);
      }
      text = await response.text();
    } else {
      text = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = () => reject(new Error('Error reading file'));
        reader.readAsText(file);
      });
    }

    return new Promise((resolve, reject) => {
      Papa.parse(text, {
        header: true,
        skipEmptyLines: true,
        transformHeader: (header) => header.trim(),
        complete: (results) => {
          if (results.errors.length > 0) {
            console.warn('CSV parsing warnings:', results.errors);
          }

          if (!Array.isArray(results.data) || results.data.length === 0) {
            reject(new Error('No data found in CSV file'));
            return;
          }

          const data = results.data
            .filter((row: any) => Object.values(row).some(value => value != null && value !== ''))
            .map((row: any, index) => {
              // Add source reference in a format that can be displayed as a tooltip
              const sourceRef = `【${index + 1}:1†source】`;
              
              return {
                ...row,
                source: typeof file === 'string' ? 'PharmAlchemy' : file.name,
                content: `${sourceRef}${Object.entries(row)
                  .filter(([_, value]) => value != null && value !== '')
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(' | ')}`
              };
            });

          resolve(data);
        },
        error: (error) => reject(error)
      });
    });
  } catch (error) {
    console.error(`Error processing file:`, error);
    throw error;
  }
}

async function processFile(file: File): Promise<DataEntry[]> {
  const fileExtension = file.name.split('.').pop()?.toLowerCase();
  let data: DataEntry[];

  try {
    if (fileExtension === 'xlsx' || fileExtension === 'xls') {
      data = await processExcelFile(file);
    } else if (fileExtension === 'csv') {
      data = await processCsvFile(file);
    } else {
      throw new Error('Unsupported file format. Please upload CSV or Excel files.');
    }

    // Remove existing data for this file if it exists
    cachedData = cachedData.filter(entry => entry.source !== file.name);
    
    // Add new data
    cachedData = [...cachedData, ...data];
    if (!userUploadedFiles.includes(file.name)) {
      userUploadedFiles.push(file.name);
    }
    
    // Save to localStorage
    saveCachedData();

    return data;
  } catch (error) {
    throw error;
  }
}

async function loadBackendData() {
  try {
    const data = await processCsvFile('ttd_drug_disease.csv');
    if (data.length > 0) {
      // Keep user uploaded data but replace PharmAlchemy data
      cachedData = [
        ...cachedData.filter(entry => entry.source !== 'PharmAlchemy'),
        ...data
      ];
      saveCachedData();
      return data.length;
    }
    return 0;
  } catch (error) {
    console.error('Error loading backend data:', error);
    throw error;
  }
}

function clearData() {
  const pharmAlchemyData = cachedData.filter(entry => entry.source === 'PharmAlchemy');
  cachedData = pharmAlchemyData;
  userUploadedFiles = [];
  saveCachedData();
  return true;
}

function getLoadedFiles(): string[] {
  return userUploadedFiles;
}

function extractRowsCommand(query: string): { type: 'top' | 'bottom' | null; count: number } | null {
  const patterns = [
    { type: 'top', regex: /(?:show|get|display)\s+(?:top|first)\s+(\d+)/i },
    { type: 'bottom', regex: /(?:show|get|display)\s+(?:bottom|last)\s+(\d+)/i },
    { type: 'top', regex: /^(?:top|first)\s+(\d+)/i },
    { type: 'bottom', regex: /^(?:bottom|last)\s+(\d+)/i }
  ];

  for (const pattern of patterns) {
    const match = query.match(pattern.regex);
    if (match) {
      return {
        type: pattern.type,
        count: parseInt(match[1], 10)
      };
    }
  }

  return null;
}

async function searchKnowledgeBase(query: string): Promise<SearchResult> {
  try {
    // Check for row commands first
    const rowCommand = extractRowsCommand(query);
    
    if (rowCommand) {
      const { type, count } = rowCommand;
      const rows = type === 'top' 
        ? cachedData.slice(0, count) 
        : cachedData.slice(-count);

      if (rows.length === 0) {
        return {
          text: "No data available to display.",
          foundInKnowledgeBase: false,
          searchDetails: {
            totalRecords: 0,
            searchTerms: [],
            conditions: [],
            requestedColumns: [],
            availableColumns: [],
            sources: []
          }
        };
      }

      const headers = Object.keys(rows[0]).filter(key => 
        key !== 'content' && key !== 'source'
      );

      return {
        text: `Showing ${type === 'top' ? 'first' : 'last'} ${rows.length} rows from the dataset.`,
        foundInKnowledgeBase: true,
        searchDetails: {
          totalRecords: rows.length,
          searchTerms: [],
          conditions: [],
          requestedColumns: headers,
          availableColumns: headers,
          sources: [...new Set(rows.map(entry => entry.source))]
        }
      };
    }

    // Regular search logic
    const searchTerms = extractSearchTerms(query);
    const relevantEntries = searchLocalData(searchTerms);

    if (relevantEntries.length === 0) {
      return {
        text: "No matching records found.",
        foundInKnowledgeBase: false,
        searchDetails: {
          totalRecords: 0,
          searchTerms,
          conditions: [],
          requestedColumns: [],
          availableColumns: [],
          sources: []
        }
      };
    }

    const headers = Object.keys(relevantEntries[0]).filter(key => 
      key !== 'content' && key !== 'source'
    );

    return {
      text: relevantEntries[0].content,
      foundInKnowledgeBase: true,
      searchDetails: {
        totalRecords: relevantEntries.length,
        searchTerms,
        conditions: [],
        requestedColumns: headers,
        availableColumns: headers,
        sources: [...new Set(relevantEntries.map(entry => entry.source))]
      }
    };
  } catch (error) {
    console.error('Error searching knowledge base:', error);
    return {
      text: "An error occurred while searching the knowledge base.",
      foundInKnowledgeBase: false,
      searchDetails: {
        totalRecords: 0,
        searchTerms: [],
        conditions: [],
        requestedColumns: [],
        availableColumns: [],
        sources: []
      }
    };
  }
}

function extractSearchTerms(query: string): string[] {
  const stopWords = new Set([
    'show', 'list', 'display', 'what', 'where', 'find', 'me', 'the', 'a', 'an',
    'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'table', 'data', 'information', 'about', 'tell', 'give', 'get', 'search',
    'top', 'bottom', 'first', 'last', 'rows'
  ]);

  return query.toLowerCase()
    .replace(/[.,?!]/g, ' ')
    .split(/\s+/)
    .filter(term => 
      term.length > 2 && 
      !stopWords.has(term) &&
      !/^\d+$/.test(term)
    );
}

function searchLocalData(terms: string[]): DataEntry[] {
  if (terms.length === 0) return [];

  return cachedData.filter(entry => {
    const entryText = Object.entries(entry)
      .filter(([key]) => key !== 'content' && key !== 'source')
      .map(([_, value]) => String(value).toLowerCase())
      .join(' ');
    
    return terms.some(term => 
      entryText.includes(term.toLowerCase())
    );
  });
}

export {
  searchKnowledgeBase,
  clearData,
  getLoadedFiles,
  loadBackendData,
  processCsvFile,
  processFile
};