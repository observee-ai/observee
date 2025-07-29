/**
 * Tool filtering strategies factory
 */

import { BaseToolFilter } from './base.js';
import { BM25Filter } from './bm25Filter.js';

export function createFilter(
  filterType: string = 'bm25',
  vectorStoreManager?: any,
  syncTools: boolean = false
): BaseToolFilter {
  switch (filterType.toLowerCase()) {
    case 'bm25':
      return new BM25Filter(true, syncTools);
    // TODO: Implement other filters
    // case 'local_embedding':
    //   return new LocalEmbeddingFilter();
    // case 'cloud':
    //   return new CloudFilter(vectorStoreManager);
    default:
      console.warn(`Unknown filter type: ${filterType}, falling back to BM25`);
      return new BM25Filter(true, syncTools);
  }
}

export { BaseToolFilter, BM25Filter };
