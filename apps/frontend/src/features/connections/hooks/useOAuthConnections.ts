"use client";

import { useQuery } from "@tanstack/react-query";
import {
  oauthConnectorsService,
  type OAuthConnection,
  type OAuthProviderItem,
} from "@/lib/api/oauthConnectorsService";

const PROVIDERS_KEY = ["oauth-providers"] as const;
const CONNECTIONS_KEY = ["oauth-connections"] as const;

/** List providers wired on this deployment. Stable per release —
 *  refetched on mount only, no polling. */
export function useOAuthProviders() {
  return useQuery<OAuthProviderItem[]>({
    queryKey: PROVIDERS_KEY,
    queryFn: () => oauthConnectorsService.listProviders(),
    staleTime: 5 * 60 * 1000,
  });
}

/** All OAuth connections owned by the current workspace. */
export function useOAuthConnections() {
  return useQuery<OAuthConnection[]>({
    queryKey: CONNECTIONS_KEY,
    queryFn: () => oauthConnectorsService.listConnections(),
  });
}

export { CONNECTIONS_KEY as OAUTH_CONNECTIONS_QUERY_KEY };
