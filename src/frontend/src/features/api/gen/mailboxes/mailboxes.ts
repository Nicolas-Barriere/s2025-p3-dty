/**
 * Generated by orval v7.10.0 🍺
 * Do not edit manually.
 * messages API
 * This is the messages API schema.
 * OpenAPI spec version: 1.0.0 (v1.0)
 */
import { useQuery } from "@tanstack/react-query";
import type {
  DataTag,
  DefinedInitialDataOptions,
  DefinedUseQueryResult,
  QueryClient,
  QueryFunction,
  QueryKey,
  UndefinedInitialDataOptions,
  UseQueryOptions,
  UseQueryResult,
} from "@tanstack/react-query";

import type {
  Mailbox,
  MailboxLight,
  MailboxesSearchListParams,
} from ".././models";

import { fetchAPI } from "../../fetch-api";

type SecondParameter<T extends (...args: never) => unknown> = Parameters<T>[1];

/**
 * ViewSet for Mailbox model.
 */
export type mailboxesListResponse200 = {
  data: Mailbox[];
  status: 200;
};

export type mailboxesListResponseComposite = mailboxesListResponse200;

export type mailboxesListResponse = mailboxesListResponseComposite & {
  headers: Headers;
};

export const getMailboxesListUrl = () => {
  return `/api/v1.0/mailboxes/`;
};

export const mailboxesList = async (
  options?: RequestInit,
): Promise<mailboxesListResponse> => {
  return fetchAPI<mailboxesListResponse>(getMailboxesListUrl(), {
    ...options,
    method: "GET",
  });
};

export const getMailboxesListQueryKey = () => {
  return [`/api/v1.0/mailboxes/`] as const;
};

export const getMailboxesListQueryOptions = <
  TData = Awaited<ReturnType<typeof mailboxesList>>,
  TError = unknown,
>(options?: {
  query?: Partial<
    UseQueryOptions<Awaited<ReturnType<typeof mailboxesList>>, TError, TData>
  >;
  request?: SecondParameter<typeof fetchAPI>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getMailboxesListQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof mailboxesList>>> = ({
    signal,
  }) => mailboxesList({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof mailboxesList>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type MailboxesListQueryResult = NonNullable<
  Awaited<ReturnType<typeof mailboxesList>>
>;
export type MailboxesListQueryError = unknown;

export function useMailboxesList<
  TData = Awaited<ReturnType<typeof mailboxesList>>,
  TError = unknown,
>(
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof mailboxesList>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof mailboxesList>>,
          TError,
          Awaited<ReturnType<typeof mailboxesList>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};
export function useMailboxesList<
  TData = Awaited<ReturnType<typeof mailboxesList>>,
  TError = unknown,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof mailboxesList>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof mailboxesList>>,
          TError,
          Awaited<ReturnType<typeof mailboxesList>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};
export function useMailboxesList<
  TData = Awaited<ReturnType<typeof mailboxesList>>,
  TError = unknown,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof mailboxesList>>, TError, TData>
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};

export function useMailboxesList<
  TData = Awaited<ReturnType<typeof mailboxesList>>,
  TError = unknown,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof mailboxesList>>, TError, TData>
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
} {
  const queryOptions = getMailboxesListQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<
    TData,
    TError
  > & { queryKey: DataTag<QueryKey, TData, TError> };

  query.queryKey = queryOptions.queryKey;

  return query;
}

/**
 * ViewSet for Mailbox model.
 */
export type mailboxesRetrieveResponse200 = {
  data: Mailbox;
  status: 200;
};

export type mailboxesRetrieveResponseComposite = mailboxesRetrieveResponse200;

export type mailboxesRetrieveResponse = mailboxesRetrieveResponseComposite & {
  headers: Headers;
};

export const getMailboxesRetrieveUrl = (id: string) => {
  return `/api/v1.0/mailboxes/${id}/`;
};

export const mailboxesRetrieve = async (
  id: string,
  options?: RequestInit,
): Promise<mailboxesRetrieveResponse> => {
  return fetchAPI<mailboxesRetrieveResponse>(getMailboxesRetrieveUrl(id), {
    ...options,
    method: "GET",
  });
};

export const getMailboxesRetrieveQueryKey = (id: string) => {
  return [`/api/v1.0/mailboxes/${id}/`] as const;
};

export const getMailboxesRetrieveQueryOptions = <
  TData = Awaited<ReturnType<typeof mailboxesRetrieve>>,
  TError = unknown,
>(
  id: string,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesRetrieve>>,
        TError,
        TData
      >
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getMailboxesRetrieveQueryKey(id);

  const queryFn: QueryFunction<
    Awaited<ReturnType<typeof mailboxesRetrieve>>
  > = ({ signal }) => mailboxesRetrieve(id, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: !!id,
    ...queryOptions,
  } as UseQueryOptions<
    Awaited<ReturnType<typeof mailboxesRetrieve>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type MailboxesRetrieveQueryResult = NonNullable<
  Awaited<ReturnType<typeof mailboxesRetrieve>>
>;
export type MailboxesRetrieveQueryError = unknown;

export function useMailboxesRetrieve<
  TData = Awaited<ReturnType<typeof mailboxesRetrieve>>,
  TError = unknown,
>(
  id: string,
  options: {
    query: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesRetrieve>>,
        TError,
        TData
      >
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof mailboxesRetrieve>>,
          TError,
          Awaited<ReturnType<typeof mailboxesRetrieve>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};
export function useMailboxesRetrieve<
  TData = Awaited<ReturnType<typeof mailboxesRetrieve>>,
  TError = unknown,
>(
  id: string,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesRetrieve>>,
        TError,
        TData
      >
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof mailboxesRetrieve>>,
          TError,
          Awaited<ReturnType<typeof mailboxesRetrieve>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};
export function useMailboxesRetrieve<
  TData = Awaited<ReturnType<typeof mailboxesRetrieve>>,
  TError = unknown,
>(
  id: string,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesRetrieve>>,
        TError,
        TData
      >
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};

export function useMailboxesRetrieve<
  TData = Awaited<ReturnType<typeof mailboxesRetrieve>>,
  TError = unknown,
>(
  id: string,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesRetrieve>>,
        TError,
        TData
      >
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
} {
  const queryOptions = getMailboxesRetrieveQueryOptions(id, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<
    TData,
    TError
  > & { queryKey: DataTag<QueryKey, TData, TError> };

  query.queryKey = queryOptions.queryKey;

  return query;
}

/**
 * Search mailboxes by domain, local part and contact name.

Query parameters:
- q: Optional search query for local part and contact name
 */
export type mailboxesSearchListResponse200 = {
  data: MailboxLight[];
  status: 200;
};

export type mailboxesSearchListResponseComposite =
  mailboxesSearchListResponse200;

export type mailboxesSearchListResponse =
  mailboxesSearchListResponseComposite & {
    headers: Headers;
  };

export const getMailboxesSearchListUrl = (
  id: string,
  params?: MailboxesSearchListParams,
) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : value.toString());
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1.0/mailboxes/${id}/search/?${stringifiedParams}`
    : `/api/v1.0/mailboxes/${id}/search/`;
};

export const mailboxesSearchList = async (
  id: string,
  params?: MailboxesSearchListParams,
  options?: RequestInit,
): Promise<mailboxesSearchListResponse> => {
  return fetchAPI<mailboxesSearchListResponse>(
    getMailboxesSearchListUrl(id, params),
    {
      ...options,
      method: "GET",
    },
  );
};

export const getMailboxesSearchListQueryKey = (
  id: string,
  params?: MailboxesSearchListParams,
) => {
  return [
    `/api/v1.0/mailboxes/${id}/search/`,
    ...(params ? [params] : []),
  ] as const;
};

export const getMailboxesSearchListQueryOptions = <
  TData = Awaited<ReturnType<typeof mailboxesSearchList>>,
  TError = unknown,
>(
  id: string,
  params?: MailboxesSearchListParams,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesSearchList>>,
        TError,
        TData
      >
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey =
    queryOptions?.queryKey ?? getMailboxesSearchListQueryKey(id, params);

  const queryFn: QueryFunction<
    Awaited<ReturnType<typeof mailboxesSearchList>>
  > = ({ signal }) =>
    mailboxesSearchList(id, params, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: !!id,
    ...queryOptions,
  } as UseQueryOptions<
    Awaited<ReturnType<typeof mailboxesSearchList>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type MailboxesSearchListQueryResult = NonNullable<
  Awaited<ReturnType<typeof mailboxesSearchList>>
>;
export type MailboxesSearchListQueryError = unknown;

export function useMailboxesSearchList<
  TData = Awaited<ReturnType<typeof mailboxesSearchList>>,
  TError = unknown,
>(
  id: string,
  params: undefined | MailboxesSearchListParams,
  options: {
    query: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesSearchList>>,
        TError,
        TData
      >
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof mailboxesSearchList>>,
          TError,
          Awaited<ReturnType<typeof mailboxesSearchList>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};
export function useMailboxesSearchList<
  TData = Awaited<ReturnType<typeof mailboxesSearchList>>,
  TError = unknown,
>(
  id: string,
  params?: MailboxesSearchListParams,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesSearchList>>,
        TError,
        TData
      >
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof mailboxesSearchList>>,
          TError,
          Awaited<ReturnType<typeof mailboxesSearchList>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};
export function useMailboxesSearchList<
  TData = Awaited<ReturnType<typeof mailboxesSearchList>>,
  TError = unknown,
>(
  id: string,
  params?: MailboxesSearchListParams,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesSearchList>>,
        TError,
        TData
      >
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
};

export function useMailboxesSearchList<
  TData = Awaited<ReturnType<typeof mailboxesSearchList>>,
  TError = unknown,
>(
  id: string,
  params?: MailboxesSearchListParams,
  options?: {
    query?: Partial<
      UseQueryOptions<
        Awaited<ReturnType<typeof mailboxesSearchList>>,
        TError,
        TData
      >
    >;
    request?: SecondParameter<typeof fetchAPI>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & {
  queryKey: DataTag<QueryKey, TData, TError>;
} {
  const queryOptions = getMailboxesSearchListQueryOptions(id, params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<
    TData,
    TError
  > & { queryKey: DataTag<QueryKey, TData, TError> };

  query.queryKey = queryOptions.queryKey;

  return query;
}
