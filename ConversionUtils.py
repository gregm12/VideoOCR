
#Convert timestamp to minutes
def time_string_to_minutes(time_string):
  if not isinstance(time_string, str):
    return None
  try:
    hours, minutes, seconds, frames = map(int, time_string.split(':'))
    total_seconds = hours * 3600 + minutes * 60 + seconds
    total_minutes = total_seconds / 60
    return total_minutes
  except ValueError:
    return None


def convert_to_float(df):
  for col in df.columns:
    try:
      df[col] = df[col].astype(float)
    except ValueError:
      df[col] = None
  return df
