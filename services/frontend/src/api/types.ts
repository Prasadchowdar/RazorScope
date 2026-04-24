/** Shared segmentation filter params passed to all filterable endpoints. */
export interface SegmentFilters {
  planId?: string;
  country?: string;
  source?: string;
  paymentMethod?: string;
}
