class TimeSheetAlgo:
    def calculate_time(self, hours):
        return hours * 3600

    def validate_time(self, hours):
        return hours > 0
