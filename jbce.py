# jbce.py
# JshBot custom exception class
# Used by all bot modules

class bot_exception(Exception):

  def __init__(self, error_type, error_details, *args):
    self.error_type = str(error_type)
    self.error_details = str(error_details)
    self.error_other = args
    other_details = ''
    for detail in args:
        other_details += '{}\n'.format(detail)
    self.error_message = "`{error_type} error: {error_details}`\n{error_others}".format(
            error_type = self.error_type,
            error_details = self.error_details,
            error_others = other_details)
            
  def __str__(self):
    return self.error_message
