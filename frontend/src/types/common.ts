/**
 * Mirrors backend/app/schemas/common.py and backend/app/models/enums.py.
 */

export type ResponseStatus = "success" | "error";

export interface BaseResponse {
  status: ResponseStatus;
}

export interface BaseMetadata {
  timestamp: string;
  request_id?: string | null;
}

export interface SuccessResponse<TData> extends BaseResponse {
  data: TData;
  metadata?: BaseMetadata | null;
}
