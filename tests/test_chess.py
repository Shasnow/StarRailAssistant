"""
中国象棋游戏测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.ChessTask import ChessBoard, ChessPiece, ChessColor, ChessPieceInfo


def test_initial_board():
    """测试初始棋盘设置"""
    board = ChessBoard()
    
    # 测试黑方将
    king = board.get_piece(0, 4)
    assert king is not None
    assert king.piece_type == ChessPiece.KING
    assert king.color == ChessColor.BLACK
    
    # 测试红方帅
    king_red = board.get_piece(9, 4)
    assert king_red is not None
    assert king_red.piece_type == ChessPiece.KING
    assert king_red.color == ChessColor.RED
    
    print("初始棋盘测试通过！")


def test_move_piece():
    """测试棋子移动"""
    board = ChessBoard()
    
    # 测试移动红方兵
    success = board.move_piece(6, 4, 5, 4)
    assert success == True
    assert board.current_player == ChessColor.BLACK
    
    # 测试移动黑方卒
    success = board.move_piece(3, 4, 4, 4)
    assert success == True
    assert board.current_player == ChessColor.RED
    
    print("棋子移动测试通过！")


def test_invalid_move():
    """测试非法移动"""
    board = ChessBoard()
    
    # 测试移动对方棋子
    success = board.move_piece(0, 4, 1, 4)
    assert success == False
    
    # 测试移动空位置
    success = board.move_piece(5, 5, 6, 5)
    assert success == False
    
    print("非法移动测试通过！")


def test_chinese_chess_rules():
    """测试中国象棋规则"""
    board = ChessBoard()
    
    # 测试车走直线
    chariot = board.get_piece(9, 0)
    assert chariot.piece_type == ChessPiece.CHARIOT
    
    # 测试马走日字
    horse = board.get_piece(9, 1)
    assert horse.piece_type == ChessPiece.HORSE
    
    # 测试象走田字
    elephant = board.get_piece(9, 2)
    assert elephant.piece_type == ChessPiece.ELEPHANT
    
    print("中国象棋规则测试通过！")


def test_game_over():
    """测试游戏结束"""
    board = ChessBoard()
    
    # 手动设置游戏结束状态
    board.game_over = True
    board.winner = ChessColor.RED
    
    # 测试移动失败
    success = board.move_piece(6, 4, 5, 4)
    assert success == False
    
    print("游戏结束测试通过！")


if __name__ == "__main__":
    print("运行中国象棋测试...")
    print("=" * 40)
    
    test_initial_board()
    test_move_piece()
    test_invalid_move()
    test_chinese_chess_rules()
    test_game_over()
    
    print("=" * 40)
    print("所有测试通过！")
