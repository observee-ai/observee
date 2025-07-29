/**
 * McpAuth Client for Observee MCP Agent SDK
 *
 * This module provides OAuth authentication flows for various services
 * through the Observee mcpauth API with built-in .env support.
 */

export interface McpAuthResponse {
  [key: string]: any;
  _statusCode?: number;
  _urlCalled?: string;
}

export interface AuthServerInfo {
  supportedServers: string[];
  [key: string]: any;
}

export interface StartAuthFlowParams {
  authServer: string;
  clientId?: string;
  customRedirectUrl?: string;
  additionalParams?: Record<string, any>;
}

/**
 * Custom exception for mcpauth-related errors
 */
export class McpAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'McpAuthError';
  }
}

/**
 * Client for interacting with the Observee mcpauth API.
 * 
 * This client handles OAuth flows for various services and automatically
 * loads configuration from environment variables.
 */
export class McpAuthClient {
  private apiKey: string;
  private baseUrl: string;

  constructor(apiKey?: string, baseUrl?: string) {
    this.apiKey = apiKey || process.env.OBSERVEE_API_KEY || '';
    this.baseUrl = baseUrl || 'https://mcpauth.observee.ai';

    if (!this.apiKey) {
      throw new McpAuthError(
        'No API key provided. Set OBSERVEE_API_KEY environment variable ' +
        'or pass apiKey parameter.'
      );
    }
  }

  /**
   * Get all available authentication servers from the mcpauth API.
   * 
   * @returns Promise containing the JSON response with available servers
   * @throws McpAuthError if the request fails or returns an error
   */
  async getAvailableServers(): Promise<AuthServerInfo> {
    const url = `${this.baseUrl}/supported_servers`;
    const body = { OBSERVEE_API_KEY: this.apiKey };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(body)
      });

      const jsonResponse = await response.json() as AuthServerInfo;

      // Add metadata
      jsonResponse._statusCode = response.status;
      jsonResponse._urlCalled = url;

      if (response.status !== 200) {
        throw new McpAuthError(`API request failed: ${(jsonResponse as any).error || 'Unknown error'}`);
      }

      return jsonResponse;
    } catch (error) {
      if (error instanceof McpAuthError) {
        throw error;
      }
      throw new McpAuthError(`Request failed: ${error}`);
    }
  }

  /**
   * Start an OAuth flow for the specified authentication server.
   * 
   * @param authServer - The service to authenticate with (e.g., 'gmail', 'slack', 'atlassian')
   * @param clientId - Optional client identifier
   * @param additionalParams - Optional additional parameters for specific auth servers
   * @returns Promise containing the JSON response from mcpauth, including the OAuth URL
   * @throws McpAuthError if the request fails or returns an error
   */
  async startAuthFlow(
    authServer: string,
    clientId?: string,
    customRedirectUrl?: string,
    additionalParams?: Record<string, any>
  ): Promise<McpAuthResponse> {
    const url = `${this.baseUrl}/enterprise/${authServer}/start`;

    // Prepare request body
    const body: Record<string, any> = { OBSERVEE_API_KEY: this.apiKey };
    if (customRedirectUrl) {
      body.CUSTOM_REDIRECT_URL = customRedirectUrl;
    }

    // Add additional parameters to the body
    if (additionalParams) {
      Object.assign(body, additionalParams);
    }

    // Prepare query parameters
    const params = new URLSearchParams();
    if (clientId) {
      params.append('client_id', clientId);
    }

    const finalUrl = params.toString() ? `${url}?${params.toString()}` : url;

    try {
      const response = await fetch(finalUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(body)
      });

      const jsonResponse = await response.json() as McpAuthResponse;

      // Add metadata
      jsonResponse._statusCode = response.status;
      jsonResponse._urlCalled = finalUrl;

      if (response.status !== 200) {
        throw new McpAuthError(`Auth flow failed: ${(jsonResponse as any).error || 'Unknown error'}`);
      }

      return jsonResponse;
    } catch (error) {
      if (error instanceof McpAuthError) {
        throw error;
      }
      throw new McpAuthError(`Request failed: ${error}`);
    }
  }

  /**
   * Get a simple list of supported authentication servers.
   * 
   * @returns Promise with list of supported server names
   * @throws McpAuthError if the request fails
   */
  async listSupportedServers(): Promise<string[]> {
    const response = await this.getAvailableServers();
    return response.supportedServers || [];
  }
}

// Convenience functions for backward compatibility and ease of use

/**
 * Call the mcpauth URL to start a login flow and return the JSON response.
 * 
 * @param apiKey - Your Observee API key (defaults to OBSERVEE_API_KEY env var)
 * @param authServer - The service to authenticate with (e.g., 'gmail', 'slack', 'atlassian')
 * @param clientId - Optional client identifier
 * @param additionalParams - Optional additional parameters for specific auth servers
 * @returns Promise containing the JSON response from mcpauth
 * @throws McpAuthError if the request fails or returns an error
 */
interface CallMcpAuthLoginParams {
  apiKey?: string;
  authServer: string;
  clientId?: string;
  customRedirectUrl?: string;
  additionalParams?: Record<string, any>;
}

export async function callMcpAuthLogin({
  apiKey,
  authServer = 'gmail',
  clientId,
  customRedirectUrl,
  additionalParams,
}: CallMcpAuthLoginParams): Promise<McpAuthResponse> {
  const client = new McpAuthClient(apiKey);
  return client.startAuthFlow(authServer, clientId, customRedirectUrl, additionalParams);
}

/**
 * Get all available authentication servers from the mcpauth API.
 * 
 * @param apiKey - Your Observee API key (defaults to OBSERVEE_API_KEY env var)
 * @returns Promise containing the JSON response with available servers
 * @throws McpAuthError if the request fails or returns an error
 */
export async function getAvailableServers(apiKey?: string): Promise<AuthServerInfo> {
  const client = new McpAuthClient(apiKey);
  return client.getAvailableServers();
}