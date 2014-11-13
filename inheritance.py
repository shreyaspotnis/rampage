class A(object):
    def __init__(self, name):
        self.name = name
        self.print_stuff()

    def print_stuff(self):
        print('A', self.name)


class B(A):
    def __init__(self, name):
        super(B, self).__init__(name)

    def print_stuff(self):
        print('B', self.name)

a = A('bla')
b = B('bla b')
