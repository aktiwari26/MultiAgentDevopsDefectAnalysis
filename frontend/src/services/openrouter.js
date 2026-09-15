const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1';

export const fetchOpenRouterModels = async (apiKey) => {
  try {
    const key = apiKey || import.meta.env.VITE_OPENROUTER_API_KEY;
    if (!key) {
      console.warn('No OpenRouter API key found.');
      return [];
    }

    const response = await fetch(`${OPENROUTER_BASE_URL}/models`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${key}`,
        'HTTP-Referer': window.location.origin,
        'X-Title': 'DevOps React',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    return data.data.map(model => {
      const id = model.id.toLowerCase();
      const name = model.name.toLowerCase();
      
      // Heuristic for classification
      const isFast = 
        id.includes('mini') || 
        id.includes('haiku') || 
        id.includes('flash') || 
        id.includes('8b') || 
        id.includes('7b') ||
        id.includes('turbo') ||
        id.includes('lite') ||
        id.includes('speed') ||
        name.includes('mini') ||
        name.includes('flash') ||
        name.includes('haiku') ||
        name.includes('lite') ||
        id.includes('small');


      const provider = model.id.split('/')[0] || 'other';

      return {
        id: model.id,
        name: model.name,
        pricing: model.pricing,
        context_length: model.context_length,
        category: isFast ? 'fast' : 'reasoning',
        provider: provider
      };
    }).sort((a, b) => a.name.localeCompare(b.name));
  } catch (error) {
    console.error('Error fetching OpenRouter models:', error);
    return [];
  }
};
