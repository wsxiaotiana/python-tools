import re
from datetime import datetime

DEFAULT_INPUT_FILE_PATH = "C:\\Users\\yanxiaotian\\Desktop\\My Clippings.txt"
DEFAULT_OUTPUT_FILE_PATH = "C:\\Users\\yanxiaotian\\Desktop\\My Clippings_english.txt"

def convert_chinese_clippings_to_english(input_file_path=DEFAULT_INPUT_FILE_PATH, output_file_path=DEFAULT_OUTPUT_FILE_PATH):
    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile, \
                open(output_file_path, 'w', encoding='utf-8') as outfile:

            for line in infile:
                # Check if the line is a metadata line that needs conversion
                # Example Chinese metadata patterns:
                # - 您在位置 101-104的标注 | 添加于 2024年5月23日星期四 下午2:56:14
                # - 您在第 30 页（位置 #500-503）的标注 | 添加于 2024年5月23日星期四 下午2:58:01
                # - 您在位置 123的笔记 | 添加于 2024年5月23日星期四 下午3:00:00
                # - 您在位置 456的书签 | 添加于 2024年5月23日星期四 下午3:01:00

                metadata_match = re.match(
                    r"^- (您在(?:第\s*\d+\s*页（)?位置\s*#?([\d-]+)(?:）)?\s*的(标注|笔记|书签))\s*\|\s*(添加于\s*(\d{4})年(\d{1,2})月(\d{1,2})日星期([一二三四五六日])\s*(上午|下午)(\d{1,2}):(\d{2}):(\d{2}))",
                    line)

                if metadata_match:
                    original_phrase_part = metadata_match.group(1)  # e.g., "您在位置 101-104的标注"
                    location_numbers = metadata_match.group(2)  # e.g., "101-104"
                    clipping_type_cn = metadata_match.group(3)  # "标注", "笔记", or "书签"

                    # original_datetime_part = metadata_match.group(4) # Full Chinese date-time string part
                    year = int(metadata_match.group(5))
                    month = int(metadata_match.group(6))
                    day = int(metadata_match.group(7))
                    weekday_cn = metadata_match.group(8)
                    am_pm_cn = metadata_match.group(9)  # "上午" or "下午"
                    hour_cn = int(metadata_match.group(10))
                    minute = int(metadata_match.group(11))
                    second = int(metadata_match.group(12))

                    # Translate clipping type
                    if clipping_type_cn == "标注":
                        clipping_type_en = "Highlight on Location"
                        if "第" in original_phrase_part and "页" in original_phrase_part:  # crude check for page info
                            # Try to extract page if present in a more complex form like "- 您在第 30 页（位置 #500-503）的标注"
                            page_loc_match = re.search(r"您在第\s*(\d+)\s*页（位置\s*#?([\d-]+)）的(标注|笔记)",
                                                       original_phrase_part)
                            if page_loc_match:
                                page_num = page_loc_match.group(1)
                                loc_num = page_loc_match.group(2)
                                clipping_type_en = f"Highlight on Page {page_num} | Location {loc_num}"
                            else:  # Fallback for simpler "location" only
                                clipping_type_en = f"Highlight on Location {location_numbers}"
                        else:
                            clipping_type_en = f"Highlight on Location {location_numbers}"
                    elif clipping_type_cn == "笔记":
                        clipping_type_en = f"Note on Location {location_numbers}"
                        if "第" in original_phrase_part and "页" in original_phrase_part:
                            page_loc_match = re.search(r"您在第\s*(\d+)\s*页（位置\s*#?([\d-]+)）的(笔记)",
                                                       original_phrase_part)
                            if page_loc_match:
                                page_num = page_loc_match.group(1)
                                loc_num = page_loc_match.group(2)
                                clipping_type_en = f"Note on Page {page_num} | Location {loc_num}"
                            else:
                                clipping_type_en = f"Note on Location {location_numbers}"
                        else:
                            clipping_type_en = f"Note on Location {location_numbers}"

                    elif clipping_type_cn == "书签":
                        clipping_type_en = f"Bookmark at Location {location_numbers}"
                        # Bookmarks usually don't have page numbers in the same way, sticking to location
                    else:
                        clipping_type_en = f"Clipping on Location {location_numbers}"  # Fallback

                    # Convert Chinese AM/PM and hour to 24-hour format for datetime object
                    hour_24 = hour_cn
                    if am_pm_cn == "下午":  # PM
                        if hour_cn < 12:
                            hour_24 = hour_cn + 12
                    elif am_pm_cn == "上午":  # AM
                        if hour_cn == 12:  # 12 AM (midnight)
                            hour_24 = 0

                    # Create datetime object
                    dt_obj = datetime(year, month, day, hour_24, minute, second)

                    # Format to English string: "Monday, May 15, 2023 10:30:45 AM"
                    # %A for full weekday name, %B for full month name, %d for day, %Y for year
                    # %I for hour (12-hour clock), %M for minute, %S for second, %p for AM/PM
                    english_date_str = dt_obj.strftime("%A, %B %d, %Y %I:%M:%S %p")

                    # Reconstruct the line
                    # Special handling if clipping_type_en already includes location due to page presence
                    if "Location" in clipping_type_en and "Page" in clipping_type_en:  # e.g. "Highlight on Page X | Location Y"
                        new_line = f"- Your {clipping_type_en} | Added on {english_date_str}\n"
                    else:
                        new_line = f"- Your {clipping_type_en} {location_numbers} | Added on {english_date_str}\n"

                    outfile.write(new_line)
                else:
                    # If it's not a metadata line or doesn't match the Chinese pattern,
                    # write it as is (this includes book titles, empty lines, and the actual notes/highlights)
                    outfile.write(line)

            print(f"Conversion complete. Output saved to: {output_file_path}")

    except FileNotFoundError:
        print(f"Error: The file {input_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# --- How to use: ---
# 1. Save the script above as a Python file (e.g., `convert_clippings.py`).
# 2. Make sure your Chinese Kindle clippings file is named `clipping.txt` (or change the filename in the script)
#    and is in the same directory as the script.
# 3. Run the script from your terminal: `python convert_clippings.py`
# 4. A new file named `clipping_en.txt` will be created with the converted identifiers.

if __name__ == "__main__":
    # You can specify different file paths here if needed:
    # convert_chinese_clippings_to_english(input_file_path="My Clippings.txt", output_file_path="My Clippings_EN.txt")
    convert_chinese_clippings_to_english()