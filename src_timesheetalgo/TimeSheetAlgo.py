class TimeSheetAlgo:
    def calculate_time(self, hours):
        return hours * 3600
    
    def format_time(self, seconds):
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    
    def validate_hours(self, hours):
        return hours >= 0 and hours <= 24
