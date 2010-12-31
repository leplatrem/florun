#!/usr/bin/python
# -*- coding: utf8 -*-

import unittest

from flow import Flow, Node, NodeNotFoundError


class TestFlow(unittest.TestCase):

    def setUp(self):
        self.flow = Flow()

    def test_addNode(self):
        self.assertEqual(self.flow.nodes, [])
        n = Node()
        self.flow.addNode(n)
        self.assertEqual(self.flow.nodes, [n])
        self.assertEqual(n.flow, self.flow)
        self.assertTrue(n in self.flow.startNodes)

    def test_removeNode(self):
        self.assertEqual(self.flow.nodes, [])
        self.assertRaises(ValueError, self.flow.removeNode, Node())
        n = Node()
        self.flow.addNode(n)
        self.flow.removeNode(n)
        self.assertFalse(n in self.flow.nodes)
        self.assertEqual(n.flow, None)

    def test_findNode(self):
        self.assertRaises(NodeNotFoundError, self.flow.findNode, 'foo')
        n = Node()
        self.flow.addNode(n)
        self.assertEqual(n, self.flow.findNode(''))


if __name__ == '__main__':
    unittest.main()
