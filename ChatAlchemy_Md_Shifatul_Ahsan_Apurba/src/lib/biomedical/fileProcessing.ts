import { openai } from '../openai';
import * as pdfjsLib from 'pdfjs-dist';

// Configure PDF.js worker
const pdfWorkerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString();

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerSrc;

interface ProcessedFile {
  content: string;
  genes: string[];
  suggestedDiseases: string[];
  summary?: string;
}

// Chunk size for text processing (approximately 350 words)
const CHUNK_SIZE = 2000; // Characters (roughly 350 words)

// Retry configuration
const MAX_RETRIES = 5;
const BASE_DELAY = 2000; // 2 seconds
const MAX_DELAY = 32000; // 32 seconds
const JITTER_FACTOR = 0.2; // 20% jitter

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function calculateDelay(attempt: number, retryAfter?: number): number {
  // Use retry-after if provided, otherwise use exponential backoff
  let delay = retryAfter ? retryAfter * 1000 : Math.min(BASE_DELAY * Math.pow(2, attempt), MAX_DELAY);
  
  // Add jitter to prevent thundering herd
  const jitter = Math.random() * JITTER_FACTOR * delay;
  return Math.floor(delay + jitter);
}

async function withRetry<T>(
  operation: () => Promise<T>,
  context: string
): Promise<T> {
  let attempt = 0;
  
  while (true) {
    try {
      return await operation();
    } catch (error: any) {
      attempt++;
      
      if (error?.response?.status === 429 && attempt <= MAX_RETRIES) {
        // Get retry delay from response headers or calculate it
        const retryAfter = parseInt(error.response.headers?.['retry-after'] || '0', 10);
        const delay = calculateDelay(attempt, retryAfter);
        
        console.log(`Rate limit hit for ${context}. Attempt ${attempt}/${MAX_RETRIES}. Retrying in ${delay/1000}s...`);
        await sleep(delay);
        continue;
      }
      
      // If we've exhausted retries or it's not a rate limit error, throw
      if (error?.response?.status === 429) {
        throw new Error(`Rate limit exceeded for ${context}. Please try again later.`);
      }
      throw error;
    }
  }
}

function splitTextIntoChunks(text: string): string[] {
  const chunks: string[] = [];
  let currentIndex = 0;

  while (currentIndex < text.length) {
    // Find a good breaking point (end of sentence) within the chunk size
    let endIndex = Math.min(currentIndex + CHUNK_SIZE, text.length);
    if (endIndex < text.length) {
      // Look for the last period within the chunk
      const lastPeriod = text.lastIndexOf('.', endIndex);
      if (lastPeriod > currentIndex) {
        endIndex = lastPeriod + 1;
      }
    }

    chunks.push(text.slice(currentIndex, endIndex).trim());
    currentIndex = endIndex;
  }

  return chunks;
}

export async function processFile(file: File): Promise<ProcessedFile> {
  try {
    const content = await readFile(file);
    const chunks = splitTextIntoChunks(content);
    
    // Process all chunks for summary generation
    const fullSummary = await withRetry(
      () => generateSummary(content),
      'summary generation'
    );

    // Process each chunk to extract genes
    const allGenes: Set<string> = new Set();
    const allDiseases: Set<string> = new Set();

    for (const chunk of chunks) {
      const entityResult = await withRetry(
        () => extractEntities(chunk),
        'entity extraction'
      );

      entityResult.genes.forEach(gene => allGenes.add(gene));
      entityResult.suggestedDiseases.forEach(disease => allDiseases.add(disease));
    }
    
    return {
      content,
      genes: Array.from(allGenes),
      suggestedDiseases: Array.from(allDiseases),
      summary: fullSummary
    };
  } catch (error: any) {
    console.error('Error processing file:', error);
    throw new Error(`Error processing file: ${error.message}`);
  }
}

async function readFile(file: File): Promise<string> {
  if (file.type === 'application/pdf') {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let text = '';
      
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        const pageText = content.items
          .map((item: any) => item.str)
          .join(' ');
        text += pageText + '\n';
      }
      
      return text;
    } catch (error: any) {
      console.error('Error reading PDF:', error);
      throw new Error('Failed to read PDF file. Please try again or use a different file.');
    }
  } else {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = (e) => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }
}

async function generateSummary(text: string): Promise<string> {
  const completion = await openai.chat.completions.create({
    model: "gpt-4-turbo-preview",
    messages: [
      {
        role: "system",
        content: `You are a biomedical research expert. Create a comprehensive summary of this research document focusing on:

1. Paper Title (if available)
2. Key Research Question/Objective (1-2 sentences)
3. Main Methodology (1-2 sentences)
4. Principal Findings (2-3 key points)
5. Implications (1 sentence)

Rules:
- Be direct and precise
- Avoid jargon and technical terms when possible
- If title is available, start with "The paper titled '[TITLE]' ..."
- Use clear paragraph breaks between sections
- Focus on factual information only
- Ensure complete sentences and proper transitions
- Do not use bullet points or numbered lists
- Do not truncate or cut off mid-sentence
- Do not use bold text or unnecessary formatting
- Aim for clarity and completeness over strict word count

Note: While aiming for conciseness, prioritize complete thoughts and proper sentence structure over word limit.`
      },
      {
        role: "user",
        content: text
      }
    ],
    temperature: 0.1,
    max_tokens: 500 // Increased to ensure complete thoughts
  });

  return completion.choices[0]?.message?.content || 
    "Unable to generate summary for this document.";
}

async function extractEntities(text: string): Promise<{ genes: string[]; suggestedDiseases: string[] }> {
  const completion = await openai.chat.completions.create({
    model: "gpt-4-turbo-preview",
    messages: [
      {
        role: "system",
        content: `You are a biomedical entity extraction expert. Your task is to extract ONLY explicitly mentioned genes and associated diseases from the text.

CRITICAL RULES:
1. For genes:
   - ONLY extract genes that are explicitly mentioned in the text
   - DO NOT infer or guess gene names
   - DO NOT include protein names or other biological entities
   - DO NOT include gene names that are part of other words or compounds
   - If uncertain about a gene symbol, DO NOT include it
   - DO NOT bold words or sentence or title

2. For diseases:
   - ONLY include diseases that are directly associated with the extracted genes
   - Use standardized disease names
   - DO NOT infer disease associations
   - If the relationship is unclear, DO NOT include the disease

Format the response as JSON with:
- "genes": array of mentioned gene in the text
- "suggestedDiseases": array of diseases with CLEAR gene associations

Remember: It's better to return fewer results than to include uncertain or incorrect entries.`
      },
      {
        role: "user",
        content: text
      }
    ],
    response_format: { type: "json_object" },
    temperature: 0.0,
    max_tokens: 500
  });

  const response = JSON.parse(completion.choices[0]?.message?.content || '{"genes":[],"suggestedDiseases":[]}');
  return {
    genes: response.genes || [],
    suggestedDiseases: response.suggestedDiseases || []
  };
}