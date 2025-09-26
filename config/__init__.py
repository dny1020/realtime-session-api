"""Configuration package utilities"""

from typing import List, Union

def parse_csv_list(value: Union[str, List[str]]) -> List[str]:
	"""Parse a comma-separated string into a list of strings. If already a list, return as-is."""
	if isinstance(value, list):
		return value
	if isinstance(value, str):
		items = [v.strip() for v in value.split(",") if v.strip()]
		return items or ["*"]
	return ["*"]